# Product Requirements Document
## Smart Adaptive Traffic Signal

### Goals
- Reduce idle wait time at traffic signals by adapting green time to real vehicle counts
- Prioritize emergency vehicles (ambulance) with immediate green
- Ensure fairness for all roads (no starvation)
- Provide a realistic 2D virtual simulation driven by real-world input

### Users
- **Commuters**: mobile Commuter page with live signal status and ETA notifications
- **Traffic Operator / Demo Viewer**: Dashboard with live video, detection, 2D simulation, controls
- **Evaluators**: Analytics page with Fixed-vs-Adaptive comparison

### Features
| ID | Feature | Description |
|----|---------|-------------|
| F1 | Adaptive timing | Green time adapts to vehicle count; max 120 s, early switch at 35 s if empty |
| F2 | Emergency priority | Ambulance detected → immediate green for that road |
| F3 | Clearance prediction | Predict time to clear current queue using discharge rates |
| F4 | Live dashboard | Real-time video with detections, signal lights, decision log |
| F5 | 2D Traffic Simulation | Top-view interactive canvas simulation of the intersection mapping virtual vehicles to real detections |
| F6 | Fixed-vs-Adaptive analytics | Compare wasted green, time saved |
| F7 | Commuter notifications | Public mobile page with light status, ETA, ambulance alerts |
| F8 | Config Management | Centralized `traffic_config.json` with secure environment variables and runtime overrides |
| F9 | ROI Calibration | API endpoints to configure Region of Interest polygons per road |

### Non-Goals
- Real city deployment
- Hardware control (stretch goal only: serial bridge to Arduino)

### Success Metrics
- ≥ 20% less wasted green in Fixed-vs-Adaptive demo
- Ambulance preemption within ≤ 5 s
- ≥ 10 FPS on normal laptop
- Fluid 2D simulation animation at 60 FPS
