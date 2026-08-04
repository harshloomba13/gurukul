class WorkflowError extends Error {
  constructor(code, message, status = 400) {
    super(message);
    this.name = 'WorkflowError';
    this.code = code;
    this.status = status;
  }
}

module.exports = { WorkflowError };
