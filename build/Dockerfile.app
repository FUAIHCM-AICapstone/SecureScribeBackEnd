ARG RUNTIME_IMAGE=runtime:latest
FROM ${RUNTIME_IMAGE}

# Set environment variables
ENV ENV=production

# Copy application code with proper permissions
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser start.sh ./start.sh

# Make start.sh executable and fix line endings (as root before switching user)
USER root
RUN chmod +x start.sh && sed -i 's/\r$//' start.sh

# Switch back to appuser
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["/bin/bash", "-c", "exec ./start.sh"]
