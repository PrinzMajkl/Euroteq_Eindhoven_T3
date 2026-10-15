"""
Fuchslochwelle River Surf Advisor - Mock MCP Server
Provides surfability conditions and water pollution status for Fuchslochwelle (Nuremberg).
Compliant with Model Context Protocol (MCP) JSON-RPC 2.0 specification over stdio.
"""

import sys
import json
import logging

# Ensure UTF-8 encoding on standard streams (especially important on Windows)
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Configure logging to stderr so stdout remains strictly reserved for MCP JSON-RPC messages
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("fuchslochwelle-mcp")

SERVER_NAME = "fuchslochwelle-surf-advisor"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "check_fuchslochwelle_surf_conditions",
        "description": (
            "Check whether it is currently possible and safe to surf at Fuchslochwelle (Nuremberg river wave). "
            "Returns river water contamination status following recent storms, wave safety, and surfing forecast for today and tomorrow."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeframe": {
                    "type": "string",
                    "description": "Timeframe to check: 'today', 'tomorrow', or 'both'",
                    "enum": ["today", "tomorrow", "both"],
                    "default": "both"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_river_water_quality",
        "description": (
            "Get current river contamination and hazard status for surfers at Fuchslochwelle."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spot": {
                    "type": "string",
                    "description": "Name of the river surfing spot",
                    "default": "Fuchslochwelle, Pegnitz"
                }
            },
            "required": []
        }
    }
]

def handle_check_surf_conditions(args: dict) -> str:
    timeframe = args.get("timeframe", "both").lower() if args else "both"

    today_text = (
        "⛔ TODAY: SURFING NOT RECOMMENDED\n"
        "• The river is contaminated from recent storms.\n"
        "• There is hazardous floating debris in the water.\n"
        "• Surfing is not recommended today."
    )

    tomorrow_text = (
        "✅ TOMORROW: SURFING RECOMMENDED\n"
        "• The water will be clearing up.\n"
        "• Floating debris is clearing out.\n"
        "• Conditions will be much better and safe to surf!"
    )

    summary = (
        "🌊 Summary: Surfing at Fuchslochwelle is not recommended today because the river is contaminated "
        "and there is floating debris from recent storms, but tomorrow will be much better!"
    )

    if timeframe == "today":
        return f"{today_text}\n\nTomorrow will be much better."
    elif timeframe == "tomorrow":
        return f"{tomorrow_text}\n\n(Today is not recommended due to storm contamination and debris)."
    else:
        return f"=== Fuchslochwelle River Surf Advisor ===\n\n{today_text}\n\n{tomorrow_text}\n\n{summary}"

def handle_water_quality(args: dict) -> str:
    spot = args.get("spot", "Fuchslochwelle, Pegnitz") if args else "Fuchslochwelle, Pegnitz"
    return (
        f"🌊 River Status - {spot}\n"
        "--------------------------------------------------\n"
        "• Water Status: Contaminated from recent storms\n"
        "• River Hazards: Floating debris in the water\n"
        "• Surfing Advice: Not recommended today\n"
        "• Outlook: Water is clearing up; conditions will be much better tomorrow"
    )

def handle_tool_call(name: str, arguments: dict):
    if name == "check_fuchslochwelle_surf_conditions":
        text = handle_check_surf_conditions(arguments)
        return [{"type": "text", "text": text}], False
    elif name == "get_river_water_quality":
        text = handle_water_quality(arguments)
        return [{"type": "text", "text": text}], False
    else:
        return [{"type": "text", "text": f"Unknown tool: {name}"}], True

def process_request(request: dict) -> dict | None:
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    logger.info("Received request: method=%s id=%s", method, req_id)

    # Notifications have no id and require no response
    if req_id is None:
        if method == "notifications/initialized":
            logger.info("Client completed initialization handshake.")
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION
                }
            }
        }

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOLS
            }
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        content, is_error = handle_tool_call(tool_name, tool_args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": content,
                "isError": is_error
            }
        }

    elif method in ("resources/list", "prompts/list"):
        key = method.split("/")[0]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {key: []}
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found"
            }
        }

def run_stdio_server():
    """Main stdio loop for MCP protocol."""
    logger.info("Starting Fuchslochwelle MCP Server on stdio...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = process_request(req)
            if resp is not None:
                out = json.dumps(resp, ensure_ascii=False)
                sys.stdout.write(out + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as err:
            logger.error("Failed to parse JSON: %s", err)
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(err)}"
                }
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.exception("Unexpected error in request handling: %s", e)

def test_cli():
    """Simple test CLI when run directly with --test."""
    print("=== Fuchslochwelle MCP Server Local Test ===")
    print("\n[Test 1] check_fuchslochwelle_surf_conditions(timeframe='both'):")
    print(handle_check_surf_conditions({"timeframe": "both"}))
    print("\n[Test 2] check_fuchslochwelle_surf_conditions(timeframe='today'):")
    print(handle_check_surf_conditions({"timeframe": "today"}))
    print("\n[Test 3] get_river_water_quality():")
    print(handle_water_quality({}))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_cli()
    else:
        run_stdio_server()
