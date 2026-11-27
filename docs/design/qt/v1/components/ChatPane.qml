import QtQuick
import QtQuick.Layouts

Rectangle {
    id: pane
    property bool agentMode: false
    color: "#ffffff"

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true; height: 66; color: "#ffffff"
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#e3ebf7" }
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 16; spacing: 9
                Rectangle { width: 34; height: 34; radius: 10; color: "#dbeafe"
                    Text { anchors.centerIn: parent; text: pane.agentMode ? "A" : "友"; color: "#1d4ed8"; font.pixelSize: 13; font.bold: true } }
                ColumnLayout { spacing: 2
                    Text { text: pane.agentMode ? "Agent 运行 #128" : "友利奈绪"; color: "#1e3a5f"; font.pixelSize: 13; font.bold: true }
                    RowLayout { spacing: 5
                        Text { text: pane.agentMode ? "本地执行器 · 8 步上限" : "私聊 · 记忆同步"; color: "#8a9bb0"; font.pixelSize: 8 }
                        Rectangle { width: 30; height: 14; radius: 7; color: "#eefbf5"; Text { anchors.centerIn: parent; text: "在线"; color: "#168b63"; font.pixelSize: 7 } }
                    }
                }
                Item { Layout.fillWidth: true }
                Rectangle { width: 78; height: 27; radius: 8; color: "#f8fbff"; border.color: "#e3ebf7"
                    Row { anchors.centerIn: parent; spacing: 4
                        Text { text: "Chat"; color: pane.agentMode ? "#607795" : "#2563eb"; font.pixelSize: 8; font.bold: !pane.agentMode }
                        Text { text: "·"; color: "#cbd5e1"; font.pixelSize: 8 }
                        Text { text: "Agent"; color: pane.agentMode ? "#2563eb" : "#607795"; font.pixelSize: 8; font.bold: pane.agentMode }
                    }
                }
                Rectangle { width: 82; height: 27; radius: 8; color: "#ffffff"; border.color: "#e3ebf7"
                    Text { anchors.centerIn: parent; text: "? 搜索当前"; color: "#607795"; font.pixelSize: 8 }
                }
                Text { text: "..."; color: "#8a9bb0"; font.pixelSize: 11 }
            }
        }

        Loader {
            Layout.fillWidth: true; Layout.fillHeight: true
            active: pane.agentMode
            visible: pane.agentMode
            source: "AgentRunPane.qml"
            Layout.leftMargin: 14; Layout.rightMargin: 14; Layout.topMargin: 14; Layout.bottomMargin: 14
        }

        ColumnLayout {
            visible: !pane.agentMode
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 0
            Item { height: 10; Layout.fillWidth: true }
            Text { Layout.alignment: Qt.AlignHCenter; text: "今天 · 18:20"; color: "#a2b2c6"; font.pixelSize: 8 }

            Repeater {
                model: [
                    { me: false, text: "你回来啦。今天外面有点冷，先喝点热的吧。", time: "18:20", memory: false },
                    { me: true, text: "刚到家。今天那个方案终于过了。", time: "18:20", memory: false },
                    { me: false, text: "那很好啊。你上次说怕过不了，我还记着呢。", time: "18:21", memory: true },
                    { me: false, text: "先把 v35.9.35 的会话菜单接上吧，桌面右键和手机左滑都要走同一套偏好。", time: "18:22", memory: false },
                    { me: true, text: "好，顺便把管理员撤回提示也做了。", time: "18:23", memory: false }
                ]
                Item {
                    Layout.fillWidth: true
                    height: bubble.height + (modelData.memory ? 40 : 26)
                    Row {
                        anchors.right: modelData.me ? parent.right : undefined
                        anchors.left: modelData.me ? undefined : parent.left
                        anchors.leftMargin: 18; anchors.rightMargin: 18
                        spacing: 7
                        Rectangle { width: 24; height: 24; radius: 7; color: modelData.me ? "#2563eb" : "#eef4ff"; anchors.bottom: parent.bottom
                            Text { anchors.centerIn: parent; text: modelData.me ? "你" : "友"; color: modelData.me ? "#ffffff" : "#1d4ed8"; font.pixelSize: 8; font.bold: true } }
                        Column {
                            spacing: 2
                            Rectangle {
                                id: bubble
                                width: Math.min(430, textItem.implicitWidth + 22)
                                height: textItem.implicitHeight + 16
                                radius: 10
                                color: modelData.me ? "#2563eb" : "#eef4ff"
                                border.color: modelData.me ? "#2563eb" : "#e3ebf7"
                                Text {
                                    id: textItem
                                    anchors.centerIn: parent
                                    width: Math.min(410, implicitWidth)
                                    text: modelData.text
                                    color: modelData.me ? "#ffffff" : "#314a65"
                                    font.pixelSize: 10
                                    wrapMode: Text.Wrap
                                }
                            }
                            Rectangle {
                                visible: modelData.memory
                                width: 190; height: 17; radius: 5; color: "#f3efff"; border.color: "#e4dcff"
                                Text { anchors.fill: parent; anchors.leftMargin: 6; text: "+ 关联记忆 · 方案汇报"; color: "#6d4fd6"; font.pixelSize: 7; verticalAlignment: Text.AlignVCenter }
                            }
                            Text {
                                text: modelData.time + (modelData.me ? " · 已读" : "")
                                color: "#a2b2c6"; font.pixelSize: 7
                                anchors.right: modelData.me ? parent.right : undefined
                            }
                        }
                    }
                }
            }
            Item { Layout.fillHeight: true; Layout.fillWidth: true }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#e3ebf7" }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 14; Layout.rightMargin: 14
            Layout.topMargin: 10; Layout.bottomMargin: 10
            spacing: 7
            RowLayout {
                spacing: 6
                Text { text: "Chat"; color: "#2563eb"; font.pixelSize: 8; font.bold: true }
                Text { text: "Code"; color: "#8a9bb0"; font.pixelSize: 8 }
                Text { text: "Agent"; color: "#8a9bb0"; font.pixelSize: 8 }
                Text { text: "Shell"; color: "#8a9bb0"; font.pixelSize: 8 }
                Item { Layout.fillWidth: true }
                Text { text: "Ctrl+Enter 发送"; color: "#a2b2c6"; font.pixelSize: 7 }
            }
            Rectangle {
                Layout.fillWidth: true; height: 44; radius: 11
                color: "#f8fbff"; border.color: "#dbe8ff"
                RowLayout { anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 7; spacing: 8
                    Text { text: pane.agentMode ? "给 Agent 下指令，或 @工具…" : "和奈绪说点什么…"; color: "#a2b2c6"; font.pixelSize: 10; Layout.fillWidth: true }
                    Rectangle { width: 48; height: 30; radius: 8; color: "#2563eb"; Text { anchors.centerIn: parent; text: "发送"; color: "#ffffff"; font.pixelSize: 9; font.bold: true } }
                }
            }
            RowLayout { spacing: 10
                Text { text: "+ 附件"; color: "#8a9bb0"; font.pixelSize: 8 }
                Text { text: "语音"; color: "#8a9bb0"; font.pixelSize: 8 }
                Text { text: "工具"; color: "#8a9bb0"; font.pixelSize: 8 }
                Item { Layout.fillWidth: true }
                Text { text: "DESIGN DRAFT · QT/QML"; color: "#c0ccda"; font.pixelSize: 7; font.letterSpacing: 1 }
            }
        }
    }
}
