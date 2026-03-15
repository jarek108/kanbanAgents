# Implementation Plan: Vibe-Kanban View-Only Dependency Graph

## Target Vision
To seamlessly integrate a "Graph View" alongside the existing "Kanban View" in the `vibe-kanban` UI. This view will act as a read-only dependency graph, taking the project's existing issues and their `blocking` relationships from the database and rendering them as a structured, automatically laid-out visual tree. 

Users will be able to switch between the Kanban and Graph tabs to immediately understand the critical path and hierarchy of their tasks without leaving the application.

## Core Technologies
- **Graph Engine:** `@xyflow/react` (React Flow) for rendering nodes, edges, panning, and zooming.
- **Auto-Layout Engine:** `dagre` (Directed Graph Layout) to mathematically calculate the X/Y coordinates of nodes based on their relationships, ensuring a clean top-down or left-to-right waterfall display.
- **Data Source:** Existing `vibe-kanban` PostgreSQL database (via existing React Query hooks).
- **UI Components:** Re-use of existing `vibe-kanban` Tailwind components (e.g., cards, badges) embedded inside custom React Flow nodes.

---

## Phase 1: Foundation & Dependencies
**Goal:** Setup the routing, UI tabs, and install the required graph libraries.

1. **Install Packages:** 
   - Navigate to `packages/local-web` and `pnpm install @xyflow/react dagre`
2. **UI Tab Integration:**
   - Modify `packages/ui/src/components/ViewNavTabs.tsx` (or the relevant project header component) to include a new "Graph" tab alongside the existing "Kanban" and "List" views.
3. **Route Scaffolding:**
   - Create a new route file: `packages/local-web/src/routes/_app.projects.$projectId.graph.tsx`.
   - Set up a basic placeholder component to ensure the router correctly loads the new tab without breaking the existing Kanban view.

## Phase 2: Data Translation Layer
**Goal:** Convert the flat arrays of `issues` and `issue_relationships` into the strict `Node` and `Edge` formats required by React Flow.

1. **Fetch Data:**
   - Utilize the existing `useProjectIssues` and `useProjectRelationships` hooks within the new Graph route component.
2. **Map Nodes:**
   - Create a `useGraphData` hook.
   - Iterate through `issues`. For each issue, generate a React Flow `Node` object.
   - *Data structure:* `{ id: issue.id, data: { label: issue.title, status: issue.status, ...issue }, position: { x: 0, y: 0 } }`
3. **Map Edges:**
   - Iterate through `issue_relationships` where `relationship_type === 'blocking'`.
   - Generate React Flow `Edge` objects.
   - *Data structure:* `{ id: rel.id, source: rel.issue_id, target: rel.related_issue_id, type: 'smoothstep', animated: true }`

## Phase 3: Auto-Layout Integration (Dagre)
**Goal:** Prevent all nodes from stacking on top of each other at `(0,0)` by programmatically calculating their coordinates.

1. **Implement Dagre Utility:**
   - Create `shared/lib/layoutGraph.ts`.
   - Initialize a new `dagre.graphlib.Graph`.
   - Feed the Nodes and Edges from Phase 2 into Dagre, specifying node dimensions (e.g., width: 300, height: 100).
   - Execute the layout algorithm (`dagre.layout(g)`).
2. **Apply Coordinates:**
   - Map over the original React Flow nodes and update their `position.x` and `position.y` with the values calculated by Dagre.

## Phase 4: Custom Node Rendering & Styling
**Goal:** Make the graph look like a native part of `vibe-kanban` rather than a generic flowchart.

1. **Create `<TaskNode />` Component:**
   - Build a custom React Flow node component that receives the issue data.
   - Wrap or re-implement the visual style of `KanbanCardContent.tsx` inside this node. It should display the Task ID, Title, Status, and Assignee avatars.
2. **Register Node Types:**
   - Pass the custom node component to the `<ReactFlow nodeTypes={{ task: TaskNode }}>` provider.
3. **Styling and Polish:**
   - Apply Tailwind classes to the edges (lines) to match the application's theme (e.g., using the `text-brand` or `border-primary` colors).
   - Ensure the `<ReactFlow />` canvas fills the remaining height of the tab window.

## Phase 5: Interaction & Review
**Goal:** Add basic quality-of-life interactions (view-only).

1. **Minimap & Controls:**
   - Enable the React Flow `<MiniMap />` and `<Controls />` components so users can easily navigate large dependency trees.
2. **Click-to-Open Panel:**
   - Implement an `onNodeClick` handler.
   - When a node is clicked, trigger the same `appNavigation.goToProjectIssue(projectId, issueId)` function used by the Kanban board to slide open the existing Task Detail Panel.
3. **Final Testing:**
   - Verify that changes made in the Task Detail Panel (e.g., changing status) immediately reflect on the Graph nodes.
   - Ensure switching between Kanban and Graph tabs is fast and memory-efficient.