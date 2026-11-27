import QtQuick
import QtQuick.Layouts

Rectangle {
    id: pane
    property bool agentMode: true
    color: "#f8fbff"
    Rectangle { anchors.left: parent.left; width: 1; height: parent.height; color: "#e3ebf7" }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 8

        Rectangle {
            visible: !pane.agentMode
            Layout.fillWidth: true; height: 73; radius: 10
            color: "#ffffff"; border.color: "#e3ebf7"
            RowLayout { anchors.fill: parent; anchors.margins: 9; spacing: 8
                Rectangle { width: 34; height: 34; radius: 10; color: "#dbeafe"; Text { anchors.centerIn: parent; text: "友"; color: "#1d4ed8"; font.pixelSize: 12; font.bold: true } }
                ColumnLayout { spacing: 2; Layout.fillWidth: true
                    Text { text: "友利奈绪"; color: "#1e3a5f"; font.pixelSize: 11; font.bold: true }
                    Text { text: "关系 · 熟 · 记忆同步"; color: "#8a9bb0"; font.pixelSize: 7 }
                }
                Rectangle { width: 7; height: 7; radius: 4; color: "#1f9d6b" }
            }
        }

        Rectangle {
            visible: !pane.agentMode
            Layout.fillWidth: true; height: 67; radius: 9
            color: "#ffffff"; border.color: "#e3ebf7"
            ColumnLayout { anchors.fill: parent; anchors.margins: 8; spacing: 3
                Text { text: "她的状态"; color: "#9aabc0"; font.pixelSize: 7; font.letterSpacing: 1.1 }
                RowLayout { Text { text: "心情"; color: "#8a9bb0"; font.pixelSize: 8 } Item { Layout.fillWidth: true } Text { text: "平静"; color: "#526982"; font.pixelSize: 8 } }
                RowLayout { Text { text: "精力"; color: "#8a9bb0"; font.pixelSize: 8 } Item { Layout.fillWidth: true } Text { text: "0.70"; color: "#526982"; font.pixelSize: 8; font.family: "Consolas" } }
                RowLayout { Text { text: "正在"; color: "#8a9bb0"; font.pixelSize: 8 } Item { Layout.fillWidth: true } Text { text: "整理方案"; color: "#526982"; font.pixelSize: 8 } }
            }
        }

        Rectangle {
            visible: pane.agentMode
            Layout.fillWidth: true; height: 66; radius: 10
            color: "#ffffff"; border.color: "#e3ebf7"
            ColumnLayout { anchors.fill: parent; anchors.margins: 9; spacing: 3
                RowLayout { spacing: 5
                    Rectangle { width: 6; height: 6; radius: 3; color: "#1f9d6b" }
                    Text { text: "AGENT 运行中"; color: "#168b63"; font.pixelSize: 7; font.letterSpacing: 1.1; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Text { text: "3 / 8"; color: "#2563eb"; font.pixelSize: 8; font.family: "Consolas" }
                }
                Text { text: "整理会话菜单实现"; color: "#1e3a5f"; font.pixelSize: 11; font.bold: true }
                Text { text: "本机工具 · 记忆已加载"; color: "#9aabc0"; font.pixelSize: 7 }
            }
        }

        ColumnLayout { visible: pane.agentMode; spacing: 4
            RowLayout { Layout.fillWidth: true
                Text { text: "上下文占用"; color: "#9aabc0"; font.pixelSize: 7 }
                Item { Layout.fillWidth: true }
                Text { text: "12.4k / 32k"; color: "#526982"; font.pixelSize: 7; font.family: "Consolas" }
            }
            Rectangle { Layout.fillWidth: true; height: 4; radius: 2; color: "#e8effa"
                Rectangle { width: parent.width * 0.39; height: 4; radius: 2; color: "#2563eb" }
            }
        }

        Text { visible: pane.agentMode; text: "工具"; color: "#9aabc0"; font.pixelSize: 7; font.letterSpacing: 1.1 }
        Repeater {
            visible: pane.agentMode
            model: [
                { name: "read_file", detail: "只读 · 已调用 4 次", state: "done" },
                { name: "search_memory", detail: "只读 · 执行中", state: "running" },
                { name: "shell", detail: "需审批 · 1 条待批", state: "warn" }
            ]
            Rectangle {
                visible: pane.agentMode
                Layout.fillWidth: true; height: 31; radius: 7
                color: "#ffffff"; border.color: modelData.state === "warn" ? "#f2d491" : "#e3ebf7"
                RowLayout { anchors.fill: parent; anchors.margins: 7; spacing: 6
                    Text { text: modelData.state === "done" ? "OK" : modelData.state === "running" ? "." : "!"; color: modelData.state === "done" ? "#1f9d6b" : modelData.state === "running" ? "#2563eb" : "#b7791f"; font.pixelSize: 9; font.bold: true }
                    ColumnLayout { spacing: 0; Layout.fillWidth: true
                        Text { text: modelData.name; color: "#314a65"; font.pixelSize: 8; font.family: "Consolas" }
                        Text { text: modelData.detail; color: "#9aabc0"; font.pixelSize: 7 }
                    }
                }
            }
        }

        Rectangle {
            visible: pane.agentMode
            Layout.fillWidth: true; height: 72; radius: 8
            color: "#fff8e6"; border.color: "#f2d491"
            ColumnLayout { anchors.fill: parent; anchors.margins: 8; spacing: 3
                RowLayout { spacing: 4
                    Text { text: "! Shell 待审批"; color: "#8a5a00"; font.pixelSize: 8; font.bold: true }
                    Item { Layout.fillWidth: true }
                    Text { text: "高风险"; color: "#b7791f"; font.pixelSize: 7 }
                }
                Text { text: "rm -rf build/"; color: "#8a5a00"; font.pixelSize: 8; font.family: "Consolas" }
                RowLayout { spacing: 5
                    Rectangle { width: 54; height: 18; radius: 5; color: "#ffffff"; border.color: "#f2d491"; Text { anchors.centerIn: parent; text: "拒绝"; color: "#8a5a00"; font.pixelSize: 7 } }
                    Rectangle { width: 54; height: 18; radius: 5; color: "#2563eb"; Text { anchors.centerIn: parent; text: "批准"; color: "#ffffff"; font.pixelSize: 7 } }
                    Item { Layout.fillWidth: true }
                }
            }
        }

        RowLayout {
            visible: !pane.agentMode
            Layout.fillWidth: true; spacing: 5
            Rectangle { Layout.fillWidth: true; height: 34; radius: 7; color: "#ffffff"; border.color: "#e3ebf7"
                Column { anchors.fill: parent; anchors.margins: 6; spacing: 1
                    Text { text: "存钱"; color: "#8a9bb0"; font.pixelSize: 7 }
                    Text { text: "¥ 0.00"; color: "#314a65"; font.pixelSize: 9; font.bold: true }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 34; radius: 7; color: "#ffffff"; border.color: "#e3ebf7"
                Column { anchors.fill: parent; anchors.margins: 6; spacing: 1
                    Text { text: "记忆"; color: "#8a9bb0"; font.pixelSize: 7 }
                    Text { text: "最近 7 天"; color: "#314a65"; font.pixelSize: 9; font.bold: true }
                }
            }
        }

        Text { text: "会话"; color: "#9aabc0"; font.pixelSize: 7; font.letterSpacing: 1.1 }
        Rectangle { Layout.fillWidth: true; height: 31; radius: 7; color: "#ffffff"; border.color: "#e3ebf7"
            RowLayout { anchors.fill: parent; anchors.margins: 7; spacing: 6
                Text { text: "A"; color: "#6d4fd6"; font.pixelSize: 9; font.bold: true }
                ColumnLayout { spacing: 0; Layout.fillWidth: true
                    Text { text: "关系 · 熟"; color: "#314a65"; font.pixelSize: 8 }
                    Text { text: "最近变化：一起改方案"; color: "#9aabc0"; font.pixelSize: 7 }
                }
                Text { text: "查看 >"; color: "#2563eb"; font.pixelSize: 7 }
            }
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.fillWidth: true; height: 52; radius: 8; color: "#eef4ff"; border.color: "#dbe8ff"
            ColumnLayout { anchors.fill: parent; anchors.margins: 8; spacing: 2
                Text { text: "LOCAL RUNTIME"; color: "#2563eb"; font.pixelSize: 7; font.letterSpacing: 1.1; font.bold: true }
                Text { text: "Python worker · 4 工具 · 无远程"; color: "#526982"; font.pixelSize: 7 }
                Text { text: "Ctrl+Shift+H 回到主窗口"; color: "#9aabc0"; font.pixelSize: 7; font.family: "Consolas" }
            }
        }
    }
}
