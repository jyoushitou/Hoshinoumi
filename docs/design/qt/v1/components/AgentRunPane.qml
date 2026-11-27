import QtQuick
import QtQuick.Layouts

ColumnLayout {
    spacing: 0

    Rectangle {
        Layout.fillWidth: true; height: 64; radius: 10
        color: "#ffffff"; border.color: "#dbe8ff"
        RowLayout { anchors.fill: parent; anchors.margins: 11; spacing: 10
            Rectangle { width: 34; height: 34; radius: 10; color: "#eef4ff"; Text { anchors.centerIn: parent; text: "A"; color: "#1d4ed8"; font.pixelSize: 14; font.bold: true } }
            ColumnLayout { spacing: 2; Layout.fillWidth: true
                RowLayout { spacing: 6
                    Text { text: "Agent 运行 #128"; color: "#1e3a5f"; font.pixelSize: 12; font.bold: true }
                    Rectangle { width: 46; height: 17; radius: 8; color: "#f0fdf7"; border.color: "#cdeee0"; Text { anchors.centerIn: parent; text: "运行中"; color: "#168b63"; font.pixelSize: 7 } }
                }
                Text { text: "整理 v35.9.35 会话菜单实现，找出可复用接口"; color: "#8a9bb0"; font.pixelSize: 8 }
            }
            ColumnLayout { spacing: 3
                Text { text: "STEP 3 / 8"; color: "#2563eb"; font.pixelSize: 7; font.family: "Consolas"; font.bold: true }
                Text { text: "12.4k tokens"; color: "#9aabc0"; font.pixelSize: 7; font.family: "Consolas" }
            }
        }
    }

    Item { height: 10 }

    Rectangle {
        Layout.fillWidth: true; Layout.fillHeight: true; radius: 10
        color: "#ffffff"; border.color: "#e3ebf7"
        ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 8

            Text { text: "指令"; color: "#9aabc0"; font.pixelSize: 7; font.letterSpacing: 1.2 }
            Rectangle {
                Layout.fillWidth: true; height: 34; radius: 8; color: "#eef4ff"; border.color: "#dbe8ff"
                Text { anchors.fill: parent; anchors.margins: 8; text: "整理 v35.9.35 会话菜单实现，找出可复用接口"; color: "#314a65"; font.pixelSize: 9; verticalAlignment: Text.AlignVCenter }
            }

            Item { height: 4 }
            Text { text: "执行轨迹"; color: "#9aabc0"; font.pixelSize: 7; font.letterSpacing: 1.2 }

            Repeater {
                model: [
                    { title: "理解目标", detail: "拆解为偏好 API、桌面菜单、移动滑动手势三个子任务", state: "done", tool: "", result: "" },
                    { title: "read_file  bot/server/routes_chat.py", detail: "读取 412 行 · 找到 recall / conversations 路由", state: "done", tool: "read_file", result: "已读取 412 行，关键路由 3 个" },
                    { title: "search_memory  会话菜单设计", detail: "检索 v35.9.35 相关设计决策与历史实现", state: "running", tool: "search_memory", result: "正在检索…" },
                    { title: "生成变更方案", detail: "等待工具结果后生成计划", state: "pending", tool: "", result: "" }
                ]
                Item {
                    Layout.fillWidth: true; height: modelData.state === "pending" ? 42 : (modelData.tool ? 62 : 48)
                    Rectangle { x: 8; y: 0; width: 2; height: parent.height; color: index === 3 ? "transparent" : "#e3ebf7" }
                    Rectangle {
                        x: 3; y: 4; width: 12; height: 12; radius: 6
                        color: modelData.state === "done" ? "#1f9d6b" : modelData.state === "running" ? "#2563eb" : "#ffffff"
                        border.color: modelData.state === "pending" ? "#cbd5e1" : "transparent"; border.width: 1
                        Text { anchors.centerIn: parent; text: modelData.state === "done" ? "OK" : modelData.state === "running" ? "." : ""; color: "#ffffff"; font.pixelSize: 8; font.bold: true }
                    }
                    ColumnLayout {
                        x: 24; width: parent.width - 28; spacing: 2
                        Text { text: modelData.title; color: modelData.state === "pending" ? "#a2b2c6" : "#314a65"; font.pixelSize: 9; font.bold: modelData.tool !== ""; font.family: modelData.tool ? "Consolas" : "Microsoft YaHei UI" }
                        Text { text: modelData.detail; color: "#9aabc0"; font.pixelSize: 8; elide: Text.ElideRight; Layout.fillWidth: true }
                        Rectangle {
                            visible: modelData.tool !== ""
                            width: parent.width; height: 19; radius: 5
                            color: modelData.state === "running" ? "#eef4ff" : "#f0fdf7"
                            border.color: modelData.state === "running" ? "#dbe8ff" : "#cdeee0"
                            Text { anchors.fill: parent; anchors.leftMargin: 6; text: modelData.result; color: modelData.state === "running" ? "#2563eb" : "#168b63"; font.pixelSize: 7; font.family: "Consolas"; verticalAlignment: Text.AlignVCenter }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true; height: 82; radius: 8; color: "#ffffff"; border.color: "#e3ebf7"
                ColumnLayout { anchors.fill: parent; anchors.margins: 8; spacing: 5
                    RowLayout { Layout.fillWidth: true
                        Text { text: "检索结果"; color: "#9aabc0"; font.pixelSize: 7; font.letterSpacing: 1.1 }
                        Item { Layout.fillWidth: true }
                        Text { text: "3 条记忆 · 1 个文件"; color: "#2563eb"; font.pixelSize: 7 }
                    }
                    Text { text: "v35.9.35 会话菜单设计：偏好 API、桌面右键、手机左滑"; color: "#526982"; font.pixelSize: 8; elide: Text.ElideRight; Layout.fillWidth: true }
                    Text { text: "routes_conversations.py / conversation_preferences / group_admin_roles"; color: "#9aabc0"; font.pixelSize: 7; font.family: "Consolas"; elide: Text.ElideRight; Layout.fillWidth: true }
                }
            }

            Item { Layout.fillHeight: true }

            Rectangle {
                Layout.fillWidth: true; height: 72; radius: 8; color: "#f8fbff"; border.color: "#e3ebf7"
                ColumnLayout { anchors.fill: parent; anchors.margins: 8; spacing: 3
                    Text { text: "下一步计划"; color: "#2563eb"; font.pixelSize: 7; font.letterSpacing: 1.1; font.bold: true }
                    Text { text: "1. 复用 conversation_preferences，补桌面右键与手机左滑"; color: "#526982"; font.pixelSize: 8 }
                    Text { text: "2. 管理员/撤回提示走 group_admin_roles + group_settings"; color: "#526982"; font.pixelSize: 8 }
                    Text { text: "3. 最后补 API 回归与三端截图"; color: "#9aabc0"; font.pixelSize: 8 }
                }
            }

            Rectangle {
                Layout.fillWidth: true; height: 37; radius: 8; color: "#fff8e6"; border.color: "#f2d491"
                RowLayout { anchors.fill: parent; anchors.margins: 8; spacing: 7
                    Text { text: "!"; color: "#b7791f"; font.pixelSize: 11 }
                    Text { text: "Shell 待审批：rm -rf build/"; color: "#8a5a00"; font.pixelSize: 8; Layout.fillWidth: true }
                    Rectangle { width: 44; height: 20; radius: 6; color: "#ffffff"; border.color: "#f2d491"; Text { anchors.centerIn: parent; text: "查看 >"; color: "#8a5a00"; font.pixelSize: 7 } }
                }
            }
        }
    }
}
