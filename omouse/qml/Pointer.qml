// Crosshairs, a spotlight and a highlight ring — whatever the CLI asked for, drawn
// over everything and *through* to everything: `mask: Region {}` means every click,
// scroll and drag reaches the application underneath. The overlay is only ever seen.
//
// Because it cannot see the pointer either, the position arrives on a pipe from
// `omarchy-mouse-utils track`, which reads Hyprland's socket directly.
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import QtQuick

ShellRoot {
  id: root

  readonly property var options: JSON.parse(Quickshell.env("OMARCHY_MOUSE_OPTIONS") || "{}")
  readonly property string mode: options.mode || "crosshairs"     // crosshairs | spotlight | ring
  readonly property color accent: options.accent || "#ff5555"
  readonly property int thickness: options.thickness || 2
  readonly property int radius: options.radius || 110
  readonly property real dimming: options.dim !== undefined ? options.dim : 0.55
  readonly property int fadeAfter: options.fade_after || 0         // ms, 0 = stay up

  property real cursorX: -1000
  property real cursorY: -1000
  property bool seen: false

  PanelWindow {
    id: panel
    visible: true
    anchors { top: true; bottom: true; left: true; right: true }
    color: "transparent"
    WlrLayershell.namespace: "omarchy-mouse-utils"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    exclusionMode: ExclusionMode.Ignore
    // The empty region is the whole point: nothing here takes input.
    mask: Region {}

    // ---------------------------------------------------------------- spotlight
    // Everything dark except a circle around the pointer. The hole is punched with
    // destination-out rather than built from rectangles: a rounded rectangle never
    // paints the corners of its own bounding box, which leaves four bright wedges
    // around the circle.
    Canvas {
      id: spotlight
      anchors.fill: parent
      visible: root.mode === "spotlight" && root.seen
      renderStrategy: Canvas.Immediate

      onPaint: {
        const ctx = getContext("2d")
        ctx.reset()
        ctx.fillStyle = Qt.rgba(0, 0, 0, root.dimming)
        ctx.fillRect(0, 0, width, height)
        ctx.globalCompositeOperation = "destination-out"
        ctx.beginPath()
        ctx.arc(root.cursorX, root.cursorY, root.radius, 0, Math.PI * 2)
        ctx.fill()
        ctx.globalCompositeOperation = "source-over"
        ctx.strokeStyle = root.accent
        ctx.lineWidth = root.thickness
        ctx.beginPath()
        ctx.arc(root.cursorX, root.cursorY, root.radius, 0, Math.PI * 2)
        ctx.stroke()
      }
    }

    // ---------------------------------------------------------------- crosshairs
    Item {
      anchors.fill: parent
      visible: root.mode === "crosshairs" && root.seen

      Rectangle {
        x: 0; width: parent.width
        y: root.cursorY - root.thickness / 2; height: root.thickness
        color: root.accent
        opacity: 0.85
      }
      Rectangle {
        y: 0; height: parent.height
        x: root.cursorX - root.thickness / 2; width: root.thickness
        color: root.accent
        opacity: 0.85
      }
      // A gap around the pointer, so the lines do not cover what they point at.
      Rectangle {
        x: root.cursorX - 14; y: root.cursorY - 14
        width: 28; height: 28; radius: 14
        color: "transparent"
        border.color: root.accent
        border.width: root.thickness
      }
    }

    // ---------------------------------------------------------------- ring
    Rectangle {
      visible: root.mode === "ring" && root.seen
      x: root.cursorX - root.radius / 2
      y: root.cursorY - root.radius / 2
      width: root.radius; height: root.radius
      radius: width / 2
      color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.20)
      border.color: root.accent
      border.width: root.thickness
    }
  }

  // ---------------------------------------------------------------- the feed
  Process {
    id: tracker
    running: true
    command: ["omarchy-mouse-utils", "track"]
    stdout: SplitParser {
      onRead: (line) => {
        const parts = line.trim().split(" ")
        if (parts.length !== 2) return
        root.cursorX = parseInt(parts[0])
        root.cursorY = parseInt(parts[1])
        root.seen = true
        if (root.mode === "spotlight") spotlight.requestPaint()
        if (root.fadeAfter > 0) fade.restart()
      }
    }
    onExited: Qt.quit()          // no feed, nothing to draw
  }

  // Find-my-mouse behaviour: show it while the pointer moves, then get out of the way.
  Timer {
    id: fade
    interval: root.fadeAfter > 0 ? root.fadeAfter : 1000
    onTriggered: Qt.quit()
  }
}
