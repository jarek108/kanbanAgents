# SynthBoard: 35-Task Technical Breakdown

This document outlines the 35 specific technical tasks required to build SynthBoard, including their dependencies.

### Infrastructure & Project Setup
1. Initialize the monorepo structure using Nx, creating empty projects for the React frontend, Node.js backend, and shared TypeScript types. Establish ESLint and Prettier configurations for consistent code styling across the workspace. (Blocked by: None)
2. Set up the local development environment with Docker Compose, including containers for PostgreSQL (database) and Redis (for WebSocket pub/sub and caching). (Blocked by: 1)
3. Configure the CI/CD pipeline using GitHub Actions to run type-checking, linting, and unit tests on every pull request. Add a deployment step to push the built frontend to Vercel and the backend to a managed container service like AWS ECS or Render. (Blocked by: 1)
4. Establish the database schema in PostgreSQL using an ORM like Prisma or Drizzle. Create initial models for User, Board, BoardElement, and DataConnector. (Blocked by: 2)
5. Implement basic JWT-based authentication in the Node.js backend. Create endpoints for user registration, login, and token refresh. (Blocked by: 4)

### Backend Core & Real-time Infrastructure
6. Integrate Socket.io into the Express server to handle real-time WebSocket connections. Implement an authentication middleware for Socket.io to ensure only verified users can connect. (Blocked by: 5)
7. Implement Redis adapter for Socket.io to allow the backend to scale horizontally across multiple instances while maintaining a single source of truth for broadcasted events. (Blocked by: 6)
8. Create the RoomManager service to handle users joining and leaving specific board sessions. Broadcast user presence events (join, leave, cursor position) to all other connected clients in the room. (Blocked by: 7)
9. Implement the core event ingestion pipeline for board edits. Create handlers for element_created, element_updated, and element_deleted events, ensuring they are validated before broadcasting to other clients. (Blocked by: 8)
10. Develop a debounced persistence layer that batches incoming board edits and saves the current board state (the serialized canvas JSON) to the PostgreSQL database every few seconds to prevent data loss. (Blocked by: 9)

### Frontend Core & Canvas Setup
11. Initialize the React frontend with Vite and configure Tailwind CSS for styling the application UI (sidebars, toolbars, modals). (Blocked by: 1)
12. Integrate Fabric.js into a React component to serve as the core rendering surface. Implement basic infinite panning and zooming capabilities using mouse wheel and middle-click drag events. (Blocked by: 11)
13. Create a state management store (using Zustand or Redux Toolkit) to synchronize the local Fabric.js canvas state with the incoming and outgoing WebSocket events. (Blocked by: 9, 12)
14. Implement the CursorLayer overlay. Render custom SVG cursors with user names that animate smoothly based on the presence events received via WebSockets. (Blocked by: 8, 13)
15. Develop the conflict resolution strategy on the frontend. Implement logic to handle receiving an element_updated event for an object that the local user is currently actively modifying (e.g., locking the object or prioritizing the remote change). (Blocked by: 13)

### Standard Whiteboarding Features
16. Build the "Sticky Note" tool. Allow users to drag a sticky note onto the canvas, double-click to edit text, and change its background color via a floating context menu. (Blocked by: 12, 13)
17. Implement the "Connector Line" tool. Allow users to draw bezier curves between specific anchor points on sticky notes and other elements, ensuring the lines update dynamically when the connected objects are moved. (Blocked by: 16)
18. Add the "Freehand Drawing" tool utilizing Fabric.js's native brush capabilities. Ensure stroke color, width, and opacity are configurable from the main toolbar. (Blocked by: 12)
19. Develop the "Selection and Grouping" logic. Allow users to drag a selection box to highlight multiple elements, group them together, and move/scale them as a single unit. (Blocked by: 16, 18)
20. Implement a rich text editor integration (like Quill or Slate) within Fabric.js text boxes to support bold, italic, lists, and basic formatting within sticky notes and text blocks. (Blocked by: 16)

### Data Connectors & Integrations
21. Create the DataConnector backend service. Implement a generic HTTP polling mechanism that can fetch JSON data from a user-provided REST API endpoint at configurable intervals. (Blocked by: 4)
22. Implement a CSV parser utility on the backend to allow users to upload static datasets. Store the parsed datasets in a dedicated, queryable format (like JSONB columns or a lightweight time-series table). (Blocked by: 4)
23. Develop the frontend "Data Source Manager" modal. Allow users to define new REST API connectors, configure authentication headers, and map JSON response fields to standard variables (e.g., mapping response.data.value to a metric called "Revenue"). (Blocked by: 11, 21)
24. Create a lightweight query engine on the backend to allow widgets to request aggregated data (e.g., sum, average, count) from the stored CSV datasets or the latest polled API results. (Blocked by: 21, 22)

### Data Visualization Widgets
25. Integrate a charting library like Recharts or Chart.js into custom Fabric.js objects. (Blocked by: 12)
26. Build the "Metric Card" widget. This element displays a single large number (e.g., Total Users) with a trend indicator (up/down arrow) and automatically updates when the underlying connected data source changes. (Blocked by: 24, 25)
27. Develop the "Line Chart" widget. Allow users to drop the widget on the board, select a connected data source, define the X/Y axes, and see live data flow into the chart. (Blocked by: 24, 25)
28. Implement the "Bar Chart" widget, including configuration options for grouped or stacked bars, and color customization mapped to specific data categories. (Blocked by: 24, 25)
29. Create a "Data Table" widget that renders a paginated grid of raw data onto the canvas, useful for inspecting the exact values behind the charts. (Blocked by: 24, 25)

### Refinement & User Experience
30. Implement a minimap navigation tool in the bottom right corner of the UI, showing a zoomed-out preview of the entire board and allowing users to click to jump to specific areas. (Blocked by: 12)
31. Develop a "Follow Me" feature. When a presenter clicks "Follow Me," force all other connected clients in the room to smoothly pan and zoom their canvas to match the presenter's viewport. (Blocked by: 8, 12)
32. Add an undo/redo stack on the frontend. Capture localized snapshots of the canvas state before changes, allowing users to hit Ctrl+Z to revert mistakes, syncing the reversion via WebSockets. (Blocked by: 13, 15)
33. Implement export functionality. Allow users to export the current view of the canvas, or a specific grouped selection, as a high-resolution PNG or PDF. (Blocked by: 12, 19)
34. Build a comprehensive "Board Dashboard" view where users can see their recently accessed boards, duplicate templates, and manage user sharing permissions (View-only vs. Edit access). (Blocked by: 4, 11)
35. Conduct performance profiling and optimization. Implement object culling in Fabric.js so elements outside the current viewport are not rendered, ensuring smooth 60fps performance even on boards with thousands of data widgets and sticky notes. (Blocked by: 12, 26, 27)
