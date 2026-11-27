import QtQuick
import QtQuick.Layouts
import "components"

Rectangle {
    id: root
    width: 1440
    height: 900
    color: "#f2f7fd"
    property bool agentMode: true

    TitleBar { id: title; width: parent.width; height: 34; y: 0 }

    Row {
        y: 34
        width: parent.width
        height: parent.height - 34

        NavRail { width: 64; height: parent.height; activeKey: root.agentMode ? "agent" : "chat" }
        ConversationPane { width: 292; height: parent.height; activeKey: root.agentMode ? "agent" : "chat" }
        ChatPane { width: parent.width - 64 - 292 - 304; height: parent.height; agentMode: root.agentMode }
        ContextPane { width: 304; height: parent.height; agentMode: root.agentMode }
    }
}
