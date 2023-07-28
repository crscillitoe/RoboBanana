from functools import wraps
from config import Config
from quart import request, make_response, jsonify
import os
import sys

# directory reach
current_directory = os.path.dirname(os.path.realpath(__file__))
parent_directory = os.path.dirname(current_directory)

# setting path
sys.path.append(parent_directory)


# Authentication decorator
def token_required(f):
    @wraps(f)
    async def decorator(*args, **kwargs):
        token = None
        # ensure the jwt-token is passed with the headers
        if "x-access-token" in request.headers:
            token = request.headers["x-access-token"]
        if not token:  # throw error if no token provided
            return await make_response(
                jsonify({"message": "A valid token is missing!"}), 401
            )

        if token != Config.CONFIG["Server"]["AuthToken"]:
            return await make_response(
                jsonify({"message": "A valid token is missing!"}), 401
            )

        return await f(*args, **kwargs)

    return decorator
