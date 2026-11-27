import QtQuick
import QtQuick.Layouts

Rectangle {
    id: pane
    property string activeKey: "agent"
    color: "#f8fbff"
    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: "#e3ebf7" }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true; height: 62
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12
                ColumnLayout {
                    spacing: 1
                    Text { text: "HOSHINOUMI"; color: "#1e3a5f"; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.8 }
                    Text { text: "AGENT CONSOLE"; color: "#9aabc0"; font.pixelSize: 7; font.letterSpacing: 1.2 }
                }
                Item { Layout.fillWidth: true }
                Rectangle { width: 44; height: 18; radius: 9; color: "#ffffff"; border.color: "#dbe8ff"; Text { anchors.centerIn: parent; text: "QT 0.1"; color: "#526982"; font.pixelSize: 7 } }
            }
        }

        Rectangle {
            Layout.leftMargin: 12; Layout.rightMargin: 12; Layout.fillWidth: true; height: 32; radius: 9
            color: "#ffffff"; border.color: "#e3ebf7"
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 9; spacing: 6
                Text { text: "?"; color: "#9aabc0"; font.pixelSize: 12 }
                Text { text: "搜索会话 / 运行 / 工具"; color: "#a2b2c6"; font.pixelSize: 9; Layout.fillWidth: true }
                Rectangle { width: 28; height: 17; radius: 4; color: "#f8fbff"; border.color: "#e3ebf7"; Text { anchors.centerIn: parent; text: "具K"; color: "#9aabc0"; font.pixelSize: 7; font.family: "Consolas" } }
            }
            Layout.bottomMargin: 12
        }

        RowLayout {
            Layout.leftMargin: 16; Layout.rightMargin: 16; Layout.fillWidth: true
            Text { text: "运行中"; color: "#9aabc0"; font.pixelSize: 8; font.letterSpacing: 1.2 }
            Item { Layout.fillWidth: true }
            Rectangle { width: 16; height: 14; radius: 7; color: "#eef4ff"; Text { anchors.centerIn: parent; text: "1"; color: "#2563eb"; font.pixelSize: 7 } }
            Layout.bottomMargin: 5
        }

        Rectangle {
            Layout.leftMargin: 8; Layout.rightMargin: 8; Layout.fillWidth: true; height: 48; radius: 10
            color: "#e7f0ff"; border.color: "#c7dcff"
            RowLayout {
                anchors.fill: parent; anchors.margins: 8; spacing: 8
                Rectangle { width: 30; height: 30; radius: 9; color: "#dbeafe"; Text { anchors.centerIn: parent; text: "A"; color: "#1d4ed8"; font.pixelSize: 13; font.bold: true } }
                ColumnLayout { spacing: 2; Layout.fillWidth: true
                    Text { text: "Agent 运行 #128"; color: "#1e3a5f"; font.pixelSize: 10; font.bold: true }
                    Text { text: "第 3 / 8 步 · 检索工具"; color: "#7d8ca3"; font.pixelSize: 8 }
                }
                Text { text: "运行"; color: "#168b63"; font.pixelSize: 7; font.bold: true }
            }
        }

        Item { height: 10 }

        RowLayout {
            Layout.leftMargin: 16; Layout.rightMargin: 16; Layout.fillWidth: true
            Text { text: "最近会话"; color: "#9aabc0"; font.pixelSize: 8; font.letterSpacing: 1.2 }
            Item { Layout.fillWidth: true }
            Text { text: "+"; color: "#2563eb"; font.pixelSize: 12 }
            Layout.bottomMargin: 4
        }

        Repeater {
            model: [
                { name: "友利奈绪", preview: "先把 v35.9.35 的会话菜单接上", time: "18:20", unread: "2", glyph: "友", active: false },
                { name: "代码模式", preview: "独立会话 · 记忆共享", time: "17:54", unread: "", glyph: "具", active: false },
                { name: "星之海学园", preview: "[图片] 晚上的教室", time: "昨天", unread: "5", glyph: "星", active: false },
                { name: "摄影部", preview: "周末去海边拍吗", time: "昨天", unread: "", glyph: "摄", active: false },
                { name: "NapCat 测试群", preview: "消息同步测试", time: "11/25", unread: "", glyph: "测", active: false }
            ]
            Item {
                Layout.leftMargin: 8; Layout.rightMargin: 8; Layout.fillWidth: true; height: 45
                Rectangle { anchors.fill: parent; radius: 9; color: hover.hovered ? "#eef4ff" : "transparent"
                    RowLayout { anchors.fill: parent; anchors.margins: 7; spacing: 8
                        Rectangle { width: 30; height: 30; radius: 9; color: modelData.glyph === "友" ? "#dbeafe" : "#eef4ff"
                            Text { anchors.centerIn: parent; text: modelData.glyph; color: "#1d4ed8"; font.pixelSize: 11; font.bold: true }
                        }
                        ColumnLayout { spacing: 1; Layout.fillWidth: true
                            Text { text: modelData.name; color: "#1e3a5f"; font.pixelSize: 10; font.bold: true }
                            Text { text: modelData.preview; color: "#8a9bb0"; font.pixelSize: 8; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        ColumnLayout { spacing: 2
                            Text { text: modelData.time; color: "#9aabc0"; font.pixelSize: 7 }
                            Rectangle { visible: modelData.unread !== ""; width: 15; height: 14; radius: 7; color: "#2563eb"
                                Text { anchors.centerIn: parent; text: modelData.unread; color: "#ffffff"; font.pixelSize: 7; font.bold: true }
                            }
                        }
                    }
                    HoverHandler { id: hover }
                }
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.leftMargin: 12; Layout.rightMargin: 12; Layout.fillWidth: true; height: 46; radius: 9
            color: "#ffffff"; border.color: "#e3ebf7"
            ColumnLayout { anchors.fill: parent; anchors.margins: 7; spacing: 1
                RowLayout { spacing: 4
                    Rectangle { width: 5; height: 5; radius: 3; color: "#1f9d6b" }
                    Text { text: "本地后端已连接"; color: "#168b63"; font.pixelSize: 8 }
                    Item { Layout.fillWidth: true }
                    Text { text: "24ms"; color: "#9aabc0"; font.pixelSize: 7; font.family: "Consolas" }
                }
                Text { text: "127.0.0.1:27005 · schema 35"; color: "#9aabc0"; font.pixelSize: 7; font.family: "Consolas" }
            }
        }
        Item { height: 9 }
    }
}
