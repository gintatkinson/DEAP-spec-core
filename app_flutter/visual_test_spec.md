# Visual, Layout, and Blending Conformance Test Case Specification

This document defines the complete visual test suite required to detect rendering, tile loading, layout splitting, and label collision defects on the 3D globe.

---

## 1. Setup & Preconditions

*   **Viewport Surface Size**: Force the viewport size to `1920x1080` (landscape) or `1080x1920` (portrait) to test layout adaptability.
*   **Database Seeding**: Seed the database with high-density nodes in close proximity (e.g., Tokyo region nodes) and nodes in space/underwater.
*   **Map Configuration**: Active 3D Globe with Satellite Map and 3D Surface Elevation enabled.
*   **Camera Coordinate Initialization**:
    *   **Far Zoom**: `VirtualCamera(latitude: 35.6074, longitude: 140.1063, altitude: 6378137.0 + 2096002.56)`
    *   **Close Zoom**: `VirtualCamera(latitude: 35.6074, longitude: 140.1063, altitude: 6378137.0 + 500.0)`

---

## 2. Test Execution & Assertions

### Step 1: Viewport Instance Count & Alignment Assertion (Layout Splitting Bug)
*   **Objective**: Detect if the flex layout incorrectly spawns duplicate viewport canvases.
*   **Verification Method**:
    1. Query the widget tree for the `Scene3DViewport` widget type:
       ```dart
       final viewportFinder = find.byType(Scene3DViewport);
       ```
    2. Assert that exactly one instance of the viewport is mounted:
       ```dart
       expect(viewportFinder, findsOneWidget);
       ```
    3. If multiple viewports exist, the test must fail immediately to prevent duplicate, misaligned globes from rendering simultaneously.

### Step 2: Automated Edge Detection for Straight Tile Seams
*   **Objective**: Detect if the tile is drawn as a flat rectangle with straight, uncurved boundaries instead of being warped onto the sphere.
*   **Verification Method**:
    1. Capture the image byte buffer of the viewport.
    2. Apply a horizontal and vertical Sobel operator (edge detection filter) to the image buffer.
    3. Search for long, continuous, straight-line segments of high-contrast edges.
    4. Assert that no straight-line edge segment aligns with the bounding box of a tile. Projected sphere tiles must only display curved or soft-blended boundaries.

### Step 3: Boundary Color/Brightness Discontinuity Check
*   **Objective**: Detect if a tile has a severe color mismatch (bright green/blue) against the dark base layer.
*   **Verification Method**:
    1. Identify the boundary pixels where the rendered tile coordinates meet the surrounding background globe sphere.
    2. Sample the color values (RGB/HSL) on the inside edge of the tile and the outside edge of the background.
    3. Calculate the delta difference in color value ($\Delta E$ in the CIELAB color space).
    4. Assert that the color difference is within acceptable limits:
       ```dart
       expect(deltaEColorDifference, lessThan(15.0));
       ```
       This verifies that the tile edge blends smoothly with the surrounding base sphere without a sharp color step-change.

### Step 4: Localized Detail (LOD) Resolution Contrast Check
*   **Objective**: Detect if one tile is sharp while all adjacent tiles are extremely blurry or missing.
*   **Verification Method**:
    1. Sample two equal-sized pixel patches: `Patch A` (center of the loaded tile) and `Patch B` (an adjacent area of the globe).
    2. Apply a Discrete Cosine Transform (DCT) or Laplacian filter to both patches to measure the frequency of detail (texture sharpness).
    3. If `Patch A` contains high-frequency details (texture) but `Patch B` contains almost none, and the transition between them is immediate rather than a gradual gradient, the test fails.
    4. Assert that the texture detail difference between adjacent visible tiles is below a maximum variance threshold to ensure smooth Level-of-Detail transitions.

### Step 5: Stuck Loading State Timeout Assertion (Infinite Loading Spinner)
*   **Objective**: Detect if the asynchronous tile loader is stuck in an infinite loading cycle.
*   **Verification Method**:
    1. Query the state of the rendering engine or search for the loading spinner indicator:
       ```dart
       final spinnerFinder = find.byKey(const Key('tile_loading_spinner'));
       ```
    2. Pump the widget tree with a timeout limit (e.g., `tester.pumpAndSettle(const Duration(seconds: 5))` or loop pump up to 5 seconds).
    3. Assert that the loading state resolves and the spinner disappears within the timeout:
       ```dart
       expect(isTileLoading, isFalse);
       ```
       If the spinner remains visible after 5 seconds, the test fails.

### Step 6: Node Label Collision & Overlap Assertion (Text Readability)
*   **Objective**: Detect if node labels overlap and become unreadable under high-density layouts.
*   **Verification Method**:
    1. Extract the projected screen-space bounding boxes (`Rect`) of all visible node labels.
    2. Loop through all pairs of label rectangles and check for intersections:
       ```dart
       rectA.overlaps(rectB)
       ```
    3. Assert that no two text label boxes overlap by more than a minimum margin:
       ```dart
       expect(rectA.overlaps(rectB), isFalse);
       ```
       If any overlap is detected, the test fails, requiring the layout to apply a decluttering algorithm (such as vertical offsets or node clustering) to guarantee text legibility.
