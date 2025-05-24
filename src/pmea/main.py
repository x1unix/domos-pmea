import logging
from pydantic import ValidationError
from .app import Application

# Get a logger for the main module
logger = logging.getLogger(__name__) 

def main():
    try:
        app = Application.create()
        app.run()
    except ValidationError as e:
        # Format validation errors into a human-readable message
        error_messages = []
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            error_messages.append(f"{loc}: {msg}")
        
        print("Configuration error:")
        print("\n".join(error_messages))
        exit(1)

if __name__ == "__main__":
    main() 