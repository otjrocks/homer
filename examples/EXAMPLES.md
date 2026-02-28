# Example Code Review Flow

This directory contains example inputs and expected outputs for the Homer Simpson AI Code Review Agent.

## Example 1: Simple Function with Issues

### Input Diff

```diff
--- a/src/calculator.js
+++ b/src/calculator.js
@@ -1,10 +1,15 @@
 function add(a, b) {
   return a + b;
 }
 
+function divide(a, b) {
+  return a / b; // Missing zero check!
+}
+
-function subtract(a, b) {
+function multiply(a, b) {
   return a - b;
 }
 
 module.exports = { add, subtract };
```

### Expected Claude Response

```json
{
  "summary": "Added a divide function but forgot zero validation. Also noticed a potential issue with the multiply function.",
  "overall_assessment": "request_changes",
  "comments": [
    {
      "file_path": "src/calculator.js",
      "start_line": 6,
      "end_line": 6,
      "severity": "high",
      "category": "bug",
      "comment": "This will cause a divide-by-zero error if b is 0. Add validation: if (b === 0) throw new Error('Cannot divide by zero');"
    },
    {
      "file_path": "src/calculator.js",
      "start_line": 9,
      "end_line": 10,
      "severity": "low",
      "category": "readability",
      "comment": "D'oh! The function is named 'multiply' but it's actually subtracting. Did you mean to rename the function or fix the operation?"
    }
  ]
}
```

### Expected GitLab Comments

**Line 6:**
> This will cause a divide-by-zero error if b is 0. Add validation: if (b === 0) throw new Error('Cannot divide by zero');

**Line 9-10:**
> D'oh! The function is named 'multiply' but it's actually subtracting. Did you mean to rename the function or fix the operation?

### Summary Note

```
Homer AI Code Review Summary 🍩

Overall Assessment: Request Changes

Summary:
Added a divide function but forgot zero validation. Also noticed a potential issue with the multiply function.

Issue Breakdown:
- High: 1
- Medium: 0
- Low: 1
```

## Example 2: Clean Code

### Input Diff

```diff
--- a/src/utils.js
+++ b/src/utils.js
@@ -1,5 +1,17 @@
+/**
+ * Utility functions for common operations
+ */
+
+/**
+ * Checks if a value is a valid email address
+ * @param {string} email - The email to validate
+ * @returns {boolean} True if valid email
+ */
+function isValidEmail(email) {
+  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
+  return emailRegex.test(email);
+}
+
 module.exports = { isValidEmail };
```

### Expected Claude Response

```json
{
  "summary": "Nice addition! Email validation function is well-documented and follows good practices.",
  "overall_assessment": "approve",
  "comments": []
}
```

### Summary Note

```
Homer AI Code Review Summary 🍩

Overall Assessment: Approve

Summary:
Nice addition! Email validation function is well-documented and follows good practices.

Issue Breakdown:
- High: 0
- Medium: 0
- Low: 0
```

## Schema Reference

### Comment Object

```json
{
  "file_path": "src/file.js",              // Must match GitLab diff exactly
  "start_line": 42,                        // Integer, first affected line
  "end_line": 45,                          // Integer, >= start_line
  "severity": "low|medium|high",           // Issue importance
  "category": "bug|performance|security|readability|architecture|style",
  "comment": "Constructive feedback..."    // Lowercase 'D'oh!' for low severity
}
```

### Overall Assessment Values

- `approve`: Code is ready to merge
- `request_changes`: Changes recommended before merge
- `comment`: Informational feedback, not blocking

## Tips

- Low-severity issues should start with "D'oh!" for humor
- Always be constructive and helpful
- Line numbers must exist in the diff
- Single-line comments: `start_line == end_line`
- Multi-line comments: `start_line < end_line`
- Empty comments array `[]` is valid if no issues found
