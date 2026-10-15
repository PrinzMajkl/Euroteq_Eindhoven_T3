# Code & Technical Implementation

This directory contains source code, scripts, prototypes, and technical experiments for the project.

---

## Folder Structure & Key Files

| File | Description |
| --- | --- |
| [`fuchslochwelle_mcp.py`](file:///c:/Users/Michal/Documents/Github/Euroteq_Eindhoven_T3/code/fuchslochwelle_mcp.py) | Mock MCP server (stdio JSON-RPC 2.0) checking surfability and storm-related river water pollution at Fuchslochwelle (Nuremberg). |
| [`digital_twin_pollution_v5.py`](file:///c:/Users/Michal/Documents/Github/Euroteq_Eindhoven_T3/code/digital_twin_pollution_v5.py) | Digital Twin pollution simulator and telemetry server. |
| [`safe_navigation_pollution_v5.py`](file:///c:/Users/Michal/Documents/Github/Euroteq_Eindhoven_T3/code/safe_navigation_pollution_v5.py) | Safe autonomous navigation controller with pollution detection integration. |
| [`gateway_node.py`](file:///c:/Users/Michal/Documents/Github/Euroteq_Eindhoven_T3/code/gateway_node.py) | Gateway communication bridge between ROS2 navigation and Digital Twin. |

---

## MCP Server: Fuchslochwelle Surf Advisor (`fuchslochwelle_mcp.py`)

A zero-dependency stdio Model Context Protocol (MCP) server designed for demos, videos, and AI agents.

### Features
- **`check_fuchslochwelle_surf_conditions`**: Query whether surfing is currently possible and safe at Fuchslochwelle (Nuremberg). Returns advice noting that today surfing is not recommended due to storm runoff and high pollution confirmed by robot sensors, but tomorrow conditions will improve significantly.
- **`get_river_water_quality`**: Real-time in-situ telemetry measured by autonomous surface vehicle sensors (Ammonium NH3-N sewage proxy, optical turbidity, electrical conductivity, LiDAR surface obstacle detection, and river flow velocity).

### Quick Test
Run self-test via CLI:
```bash
python code/fuchslochwelle_mcp.py --test
```

### Configuration (`mcp_config.json` / Claude Desktop / Antigravity)
```json
{
  "mcpServers": {
    "fuchslochwelle": {
      "command": "python",
      "args": [
        "c:/Users/Michal/Documents/Github/Euroteq_Eindhoven_T3/code/fuchslochwelle_mcp.py"
      ]
    }
  }
}
```
