# 本地书库

把你自己合法持有的 TXT / EPUB 放在这个目录，bot 只在本机读取，不上传、不再分发。

## 支持

```text
书名.txt
书名.epub
```

- TXT：UTF-8 / GBK 自动识别
- EPUB：读取元数据、目录、正文
- 文件名即书名；EPUB 优先用元数据
- 自动分章：`第N章` / `Chapter N` / 空行分隔

## 命令

```text
!books                 列出本地书
!book import <路径>     导入一本
!book read <书名> <章节>
!book progress         当前进度
```

## 注意

- 这个目录下的书不会提交到 git
- 不要放盗版站抓下来的整本内容
- 只放你有权阅读的文本
