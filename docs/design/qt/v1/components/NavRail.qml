import QtQuick
import QtQuick.Layouts

Rectangle {
    id: rail
    property string activeKey: "agent"
    color: "#ffffff"
    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: "#e3ebf7" }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 13
        anchors.bottomMargin: 11
        spacing: 0

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 38; height: 38; radius: 12
            color: "#eef4ff"; border.color: "#dbe8ff"
            Text { anchors.centerIn: parent; text: "H"; color: "#1d4ed8"; font.pixelSize: 17; font.bold: true }
            Layout.bottomMargin: 16
        }

        Repeater {
            model: [
                { key: "chat", icon: "C", title: "会话" },
                { key: "agent", icon: "A", title: "Agent" },
                { key: "tasks", icon: "T", title: "任务" },
                { key: "memory", icon: "M", title: "记忆" },
                { key: "files", icon: "F", title: "文件" },
                { key: "tools", icon: "G", title: "工具" }
            ]
            Item {
                Layout.alignment: Qt.AlignHCenter
                width: 52; height: 42
                Rectangle {
                    width: 40; height: 40; radius: 9; anchors.centerIn: parent
                    color: rail.activeKey === modelData.key ? "#eef4ff" : (hover.hovered ? "#f4f9ff" : "transparent")
                    Rectangle {
                        visible: rail.activeKey === modelData.key
                        width: 3; height: 18; radius: 2; color: "#2563eb"
                        anchors.left: parent.left; anchors.leftMargin: -6; anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        anchors.centerIn: parent; text: modelData.icon
                        color: rail.activeKey === modelData.key ? "#1d4ed8" : "#7d8ca3"; font.pixelSize: 11; font.bold: true
                    }
                    HoverHandler { id: hover }
                }
                Text {
                    anchors.left: parent.right; anchors.leftMargin: 3; anchors.verticalCenter: parent.verticalCenter
                    text: modelData.title; color: "#7d8ca3"; font.pixelSize: 8
                    visible: false
                }
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 30; height: 30; radius: 8; color: "#f8fbff"; border.color: "#e3ebf7"
            Text { anchors.centerIn: parent; text: "S"; color: "#8a9bb0"; font.pixelSize: 10; font.bold: true }
            Layout.bottomMargin: 5
        }
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            width: 31; height: 22; radius: 6; color: "#f0fdf7"
            Row { anchors.centerIn: parent; spacing: 3
                Rectangle { width: 5; height: 5; radius: 3; color: "#1f9d6b"; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "35"; color: "#168b63"; font.pixelSize: 7; font.family: "Consolas" }
            }
        }
    }
}
