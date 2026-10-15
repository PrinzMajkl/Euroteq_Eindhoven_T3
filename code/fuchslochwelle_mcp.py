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
            "Get real-time in-situ telemetry measured by autonomous water monitoring robot sensors "
            "(Ammonium NH3-N sewage proxy, optical turbidity, electrical conductivity, LiDAR floating debris, and flow rate) "
            "at the Fuchslochwelle spot."
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
        "• Water Quality: Contaminated / Poor\n"
        "• Reason: Severe thunderstorms occurred upstream, causing heavy stormwater runoff and sewer overflow "
        "into the Pegnitz river. Autonomous robot in-situ sensors detected a severe spike in Ammonium (NH3-N at 3.85 mg/L), "
        "high optical turbidity, and elevated electrical conductivity, confirming raw sewage wash.\n"
        "• Hazards: High river pollution and floating debris detected by robot LiDAR.\n"
        "• Advice: Skip surfing today. Give the river time to flush out the post-storm pollution plume."
    )

    tomorrow_text = (
        "✅ TOMORROW: SURFING RECOMMENDED / CONDITIONS IMPROVING\n"
        "• Water Quality: Clean / Normalizing (Projected)\n"
        "• Reason: Storm runoff is clearing rapidly. Robot telemetry trends show Ammonium (NH3-N) "
        "and turbidity dropping steadily back to clean baseline levels (< 0.2 mg/L).\n"
        "• River Flow: Projected optimal ~18 m³/s with clear water and no floating debris.\n"
        "• Advice: Surfing conditions will be significantly better and safe tomorrow. Good wave shape expected!"
    )

    summary = (
        "🌊 Summary: Surfing at Fuchslochwelle is currently not recommended today because recent storms "
        "caused heavy river pollution (confirmed by robot NH3-N and turbidity sensors), but conditions will be much better tomorrow!"
    )

    if timeframe == "today":
        return f"{today_text}\n\nNote: Conditions will improve significantly tomorrow."
    elif timeframe == "tomorrow":
        return f"{tomorrow_text}\n\nContext: River was polluted today due to storm runoff, but clearing out by tomorrow."
    else:
        return f"=== Fuchslochwelle River Surf Advisor ===\n\n{today_text}\n\n{tomorrow_text}\n\n{summary}"

def handle_water_quality(args: dict) -> str:
    spot = args.get("spot", "Fuchslochwelle, Pegnitz") if args else "Fuchslochwelle, Pegnitz"
    return (
        f"📊 Autonomous Robot Sensor Telemetry - {spot}\n"
        "--------------------------------------------------\n"
        "• Deployment: PlumeTrace Autonomous Surface Vehicle (In-situ real-time sensors)\n"
        "• Status: ⚠️ POLLUTION PLUME DETECTED (Post-thunderstorm runoff)\n"
        "• Ammonium Nitrogen (NH3-N): 3.85 mg/L (ALARM: Threshold 0.60 mg/L) ❌ SEWAGE OVERFLOW PROXY\n"
        "• Turbidity: 68 NTU (Clean baseline < 5 NTU) ❌ HEAVY SEDIMENT & RUNOFF\n"
        "• Electrical Conductivity (EC): 840 µS/cm (Elevated ionic urban wash)\n"
        "• LiDAR Surface Obstacle Scan: Floating logs & debris detected within 2.5m\n"
        "• River Flow Velocity: 1.4 m/s (Discharge ~22.8 m³/s)\n"
        "• Forecast Trend: Pollution plume dispersing downstream; expected baseline recovery by tomorrow morning\n"
        "• Surfing Recommendation: Unsafe today -> Safe tomorrow"
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
