import traceback
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
from enum import Enum
import logging
import glob
import gzip
import shutil
from pathlib import Path

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    API = "api"
    NETWORK = "network"
    DATABASE = "database"
    PERMISSION = "permission"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class ErrorHandler:
    def __init__(self, settings_dir: str, max_log_size_mb: int = 10, max_log_files: int = 5):
        """Initialize the error handler.
        
        Args:
            settings_dir: Directory to store error logs and recovery data
            max_log_size_mb: Maximum size of each log file in MB
            max_log_files: Maximum number of log files to keep
        """
        self.settings_dir = settings_dir
        self.error_logs_dir = os.path.join(settings_dir, "error_logs")
        self.logger = logging.getLogger(__name__)
        self.max_log_size = max_log_size_mb * 1024 * 1024  # Convert MB to bytes
        self.max_log_files = max_log_files
        
        # Create error logs directory if it doesn't exist
        os.makedirs(self.error_logs_dir, exist_ok=True)
        
        # Initialize recovery strategies
        self.recovery_strategies = {
            ErrorCategory.API.value: {
                "actions": ["retry", "fallback", "notify"],
                "max_retries": 3,
                "cooldown": 60
            },
            ErrorCategory.NETWORK.value: {
                "actions": ["retry", "fallback", "notify"],
                "max_retries": 3,
                "cooldown": 30
            },
            ErrorCategory.RATE_LIMIT.value: {
                "actions": ["wait", "notify"],
                "cooldown": 300
            },
            ErrorCategory.VALIDATION.value: {
                "actions": ["validate", "notify"],
                "max_retries": 1
            },
            ErrorCategory.UNKNOWN.value: {
                "actions": ["notify"],
                "max_retries": 1
            }
        }
        
    def _rotate_logs(self):
        """Rotate log files if they exceed size limit."""
        try:
            # Get all log files in the directory
            log_files = glob.glob(os.path.join(self.error_logs_dir, "error_*.log"))
            log_files.sort(reverse=True)  # Sort by name (newest first)
            
            # If we have too many files, compress the oldest ones
            while len(log_files) >= self.max_log_files:
                oldest_file = log_files.pop()
                compressed_file = f"{oldest_file}.gz"
                
                # Compress the file
                with open(oldest_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove the original file
                os.remove(oldest_file)
                
                # Update log_files list
                log_files = glob.glob(os.path.join(self.error_logs_dir, "error_*.log"))
                log_files.sort(reverse=True)
            
            # Check if current log file exceeds size limit
            if log_files:
                current_log = log_files[0]
                if os.path.getsize(current_log) >= self.max_log_size:
                    # Create new log file with timestamp
                    timestamp = datetime.now().strftime("%Y_%m_%d")
                    new_log = os.path.join(self.error_logs_dir, f"error_{timestamp}.log")
                    
                    # Move current log to new file
                    shutil.move(current_log, new_log)
                    
                    # Compress old files if needed
                    self._rotate_logs()
        
        except Exception as e:
            self.logger.error(f"Error rotating logs: {str(e)}")
    
    def _get_current_log_file(self) -> str:
        """Get the current log file path, creating a new one if needed."""
        timestamp = datetime.now().strftime("%Y_%m_%d")
        log_file = os.path.join(self.error_logs_dir, f"error_{timestamp}.log")
        
        # Check if current log file exists and is within size limit
        if os.path.exists(log_file) and os.path.getsize(log_file) >= self.max_log_size:
            self._rotate_logs()
        
        return log_file

    def analyze_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze an error and determine its severity and category.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            Dict containing error analysis
        """
        error_type = type(error).__name__
        error_message = str(error)
        traceback_info = traceback.format_exc()
        
        # Determine error category
        category = self._determine_error_category(error, error_message)
        
        # Determine error severity
        severity = self._determine_error_severity(error, category, context)
        
        # Get recovery strategy
        strategy = self.recovery_strategies.get(category.value, self.recovery_strategies[ErrorCategory.UNKNOWN.value])
        
        return {
            "error_type": error_type,
            "error_message": error_message,
            "category": category.value,
            "severity": severity.value,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback_info,
            "context": context or {},
            "recovery_strategy": strategy
        }
    
    def _determine_error_category(self, error: Exception, error_message: str) -> ErrorCategory:
        """Determine the category of an error based on its type and message."""
        error_message = error_message.lower()
        
        if "api" in error_message or "openai" in error_message:
            return ErrorCategory.API
        elif "network" in error_message or "connection" in error_message:
            return ErrorCategory.NETWORK
        elif "database" in error_message or "sql" in error_message:
            return ErrorCategory.DATABASE
        elif "permission" in error_message or "access" in error_message:
            return ErrorCategory.PERMISSION
        elif "validation" in error_message or "invalid" in error_message:
            return ErrorCategory.VALIDATION
        elif "rate limit" in error_message or "too many requests" in error_message:
            return ErrorCategory.RATE_LIMIT
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_error_severity(self, error: Exception, category: ErrorCategory, context: Dict[str, Any] = None) -> ErrorSeverity:
        """Determine the severity of an error based on its category and context."""
        if category == ErrorCategory.CRITICAL:
            return ErrorSeverity.CRITICAL
        
        # Check for critical operations in context
        if context and context.get("critical_operation", False):
            return ErrorSeverity.HIGH
        
        # Rate limit errors are usually high severity
        if category == ErrorCategory.RATE_LIMIT:
            return ErrorSeverity.HIGH
        
        # API errors are usually medium severity
        if category == ErrorCategory.API:
            return ErrorSeverity.MEDIUM
        
        # Network errors are usually medium severity
        if category == ErrorCategory.NETWORK:
            return ErrorSeverity.MEDIUM
        
        # Database errors are usually high severity
        if category == ErrorCategory.DATABASE:
            return ErrorSeverity.HIGH
        
        # Permission errors are usually medium severity
        if category == ErrorCategory.PERMISSION:
            return ErrorSeverity.MEDIUM
        
        # Validation errors are usually low severity
        if category == ErrorCategory.VALIDATION:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """Log an error with analysis and recovery information.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            str: Error ID for reference
        """
        # Analyze the error
        analysis = self.analyze_error(error, context)
        
        # Generate error ID
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{analysis['error_type'][:8]}"
        
        # Add error ID to analysis
        analysis["error_id"] = error_id
        
        # Get current log file and ensure it's within size limits
        log_file = self._get_current_log_file()
        
        # Save error log
        with open(log_file, "a") as f:
            json.dump(analysis, f)
            f.write("\n")  # Add newline between entries
        
        return error_id
    
    def get_error(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve error information by ID.
        
        Args:
            error_id: The ID of the error to retrieve
            
        Returns:
            Optional[Dict]: Error information if found, None otherwise
        """
        # Search through all log files (including compressed ones)
        for log_file in glob.glob(os.path.join(self.error_logs_dir, "error_*.log*")):
            try:
                # Handle compressed files
                if log_file.endswith('.gz'):
                    with gzip.open(log_file, 'rt') as f:
                        for line in f:
                            try:
                                error_info = json.loads(line)
                                if error_info.get("error_id") == error_id:
                                    return error_info
                            except json.JSONDecodeError:
                                continue
                else:
                    with open(log_file, 'r') as f:
                        for line in f:
                            try:
                                error_info = json.loads(line)
                                if error_info.get("error_id") == error_id:
                                    return error_info
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                self.logger.error(f"Error reading log file {log_file}: {str(e)}")
                continue
        
        return None
    
    def get_recovery_actions(self, error_id: str) -> List[str]:
        """Get recommended recovery actions for an error.
        
        Args:
            error_id: The ID of the error
            
        Returns:
            List[str]: List of recommended recovery actions
        """
        error_info = self.get_error(error_id)
        if not error_info:
            return []
        
        strategy = error_info.get("recovery_strategy", {})
        return strategy.get("actions", [])
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get statistics about logged errors.
        
        Returns:
            Dict containing error statistics
        """
        stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recent_errors": []
        }
        
        # Count errors in each category and severity
        for filename in os.listdir(self.error_logs_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self.error_logs_dir, filename), "r") as f:
                    error_info = json.load(f)
                    
                    stats["total_errors"] += 1
                    
                    # Count by category
                    category = error_info["category"]
                    stats["errors_by_category"][category] = stats["errors_by_category"].get(category, 0) + 1
                    
                    # Count by severity
                    severity = error_info["severity"]
                    stats["errors_by_severity"][severity] = stats["errors_by_severity"].get(severity, 0) + 1
                    
                    # Add to recent errors
                    stats["recent_errors"].append({
                        "id": error_info["error_id"],
                        "type": error_info["error_type"],
                        "category": category,
                        "severity": severity,
                        "timestamp": error_info["timestamp"]
                    })
        
        # Sort recent errors by timestamp
        stats["recent_errors"].sort(key=lambda x: x["timestamp"], reverse=True)
        stats["recent_errors"] = stats["recent_errors"][:10]  # Keep only last 10 