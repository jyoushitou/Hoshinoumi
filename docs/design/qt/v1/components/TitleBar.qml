import QtQuick
import QtQuick.Layouts

Rectangle {
    id: bar
    height: 34
    color: "#ffffff"
    border.color: "#e3ebf7"
    border.width: 0
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#e3ebf7" }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 0
        spacing: 8
        Rectangle {
            width: 18; height: 18; radius: 5
            color: "#eef4ff"; border.color: "#dbe8ff"
            Text { anchors.centerIn: parent; text: "H"; color: "#2563eb"; font.pixelSize: 10; font.bold: true }
        }
        Text { text: "HOSHINOUMI"; color: "#1e3a5f"; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.4 }
        Rectangle { width: 1; height: 12; color: "#e3ebf7" }
        Text { text: "AGENT DESKTOP"; color: "#8a9bb0"; font.pixelSize: 8; font.letterSpacing: 1.1 }
        Item { Layout.fillWidth: true }
        Rectangle {
            height: 20; radius: 10; color: "#f0fdf7"; border.color: "#cdeee0"
            width: statusRow.width + 14
            Row { id: statusRow; anchors.centerIn: parent; spacing: 4
                Rectangle { width: 5; height: 5; radius: 3; color: "#1f9d6b"; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "本地后端 · 24ms"; color: "#168b63"; font.pixelSize: 8 }
            }
        }
        Text { text: "127.0.0.1:27005"; color: "#a2b2c6"; font.pixelSize: 8; font.family: "Consolas" }
        Item { width: 8 }
        Repeater {
            model: ["-", "[]", "X"]
            Rectangle {
                width: 30; height: 34; color: hover.hovered ? (index === 2 ? "#fee2e2" : "#eef4ff") : "transparent"
                Text { anchors.centerIn: parent; text: modelData; color: index === 2 && hover.hovered ? "#b91c1c" : "#6b7c95"; font.pixelSize: 11 }
                HoverHandler { id: hover }
            }
        }
    }
}
