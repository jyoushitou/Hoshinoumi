import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_OPENGL", "software")

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QFontDatabase, QFont
from PySide6.QtQuick import QQuickView

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "agent"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, "shots", f"{mode}.png")
    app = QGuiApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei UI", 9))
    for font in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\seguisb.ttf"):
        if os.path.exists(font):
            QFontDatabase.addApplicationFont(font)
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(os.path.join(BASE, "Main.qml")))
    if view.status() == QQuickView.Error:
        for err in view.errors():
            print(err.toString())
        return 1
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(1440, 900)
    view.rootObject().setProperty("agentMode", mode == "agent")
    view.show()

    def capture():
        image = view.grabWindow()
        os.makedirs(os.path.dirname(out), exist_ok=True)
        ok = image.save(out, "PNG")
        print(f"{out} {image.width()}x{image.height()} saved={ok}")

    QTimer.singleShot(900, capture)
    QTimer.singleShot(1400, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
