# AI access: Fuchslochwelle surf advisor (mock MCP server)

`fuchslochwelle_mcp.py` is a zero-dependency Model Context Protocol (MCP) server (JSON-RPC 2.0 over stdio). An AI
assistant such as Claude Desktop can use it to answer citizen questions about the river at the Fuchslochwelle
(Nuremberg). It backs the "citizen AI access" part of the pitch.

It is a **mock**: the answers are fixed demo values, not live data from the robot or the gateway.

## Tools

| Tool | Returns |
| --- | --- |
| `check_fuchslochwelle_surf_conditions` | Whether surfing is safe today and tomorrow after storm runoff |
| `get_river_water_quality` | Demo readings from the robot's sensor suite: NH₃-N, turbidity, electrical conductivity, LiDAR obstacles, flow |

## Run

Self-test from the repository root:

```bash
python3 lab_turtlebot/src/plumetrace/tools/ai/fuchslochwelle_mcp.py --test
```

MCP client configuration (Claude Desktop `claude_desktop_config.json`, or any MCP client); use the absolute path
of your clone:

```json
{
  "mcpServers": {
    "fuchslochwelle": {
      "command": "python3",
      "args": ["/path/to/Euroteq_Eindhoven_T3/lab_turtlebot/src/plumetrace/tools/ai/fuchslochwelle_mcp.py"]
    }
  }
}
```

Written by a teammate in the former `code/` folder; moved here on 2026-10-18 when `code/` was removed.
