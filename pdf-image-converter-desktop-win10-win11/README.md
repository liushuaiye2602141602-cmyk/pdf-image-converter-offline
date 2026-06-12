# PDF Image Converter

PDF 和图片相互转换的桌面工具，适用于办公室日常批量处理文件。

---

## 功能介绍

### PDF 转图片
- 支持批量将 PDF 转为 PNG、JPG、WebP
- 支持拖拽 PDF 文件到界面
- 支持选择页码范围（如 1-3,5,8-10）
- 支持 DPI 设置：150、200、300（默认）、600
- 每个 PDF 自动创建单独输出文件夹
- 加密或损坏的 PDF 会显示中文错误提示，不影响后续文件

### 图片转 PDF
- 支持多张图片合并为一个 PDF
- 支持每张图片单独转为 PDF
- 支持 JPG、PNG、WebP、BMP、TIFF 格式
- 支持图片排序（上移、下移、按文件名排序）
- 支持页面尺寸：原图尺寸、A4 竖版、A4 横版
- PNG 透明背景自动转为白色背景

### 图片格式转换 / 压缩
- 支持 PNG、JPG、WebP、BMP 批量转换
- 支持质量压缩（默认 90）
- 支持按宽度/高度等比例缩放、自定义宽高
- 显示转换前后文件大小对比

### PDF 合并 / 拆分 / 提取 / 删除页面
- 多个 PDF 合并为一个，支持调整顺序
- 按页拆分为多个 PDF
- 提取指定页面生成新 PDF
- 删除指定页面生成新 PDF

---

## 支持格式

| 功能 | 输入格式 | 输出格式 |
|------|----------|----------|
| PDF 转图片 | PDF | PNG、JPG、WebP |
| 图片转 PDF | JPG、PNG、WebP、BMP、TIFF | PDF |
| 图片格式转换 | PNG、JPG、WebP、BMP、TIFF | JPG、PNG、WebP |

---

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖列表：
- PySide6 — GUI 框架
- PyMuPDF — PDF 转图片
- Pillow — 图片处理
- img2pdf — 图片转 PDF
- pypdf — PDF 合并/拆分
- pyinstaller — 打包 exe

---

## 运行

```bash
python main.py
```

---

## 打包 exe

```bash
build\build_exe.bat
```

打包完成后，exe 位于 `dist\PDFImageConverter\PDFImageConverter.exe`。

---

## 项目目录

```
pdf-image-converter/
├── main.py                    # 程序入口
├── requirements.txt           # 依赖清单
├── README.md                  # 项目文档
├── config.json                # 用户配置（运行后自动生成）
├── app/
│   ├── config/
│   │   └── settings.py        # 配置管理
│   ├── services/
│   │   ├── pdf_to_image.py    # PDF 转图片
│   │   ├── image_to_pdf.py    # 图片转 PDF
│   │   ├── image_converter.py # 图片格式转换
│   │   ├── pdf_tools.py       # PDF 合并/拆分
│   │   └── file_utils.py      # 工具函数
│   ├── workers/
│   │   └── task_worker.py     # 后台线程
│   └── ui/
│       ├── main_window.py     # 主窗口
│       ├── pdf_to_image_page.py
│       ├── image_to_pdf_page.py
│       ├── image_convert_page.py
│       ├── pdf_tools_page.py
│       └── settings_page.py
├── build/
│   └── build_exe.bat          # 打包脚本
└── assets/
    └── icon.png               # 应用图标（可选）
```

---

## 常见问题

**Q：PDF 转图片不清晰怎么办？**
A：将 DPI 调高，建议选择 300 或 600。默认 300 已适合打印。

**Q：图片转 PDF 背景变黑怎么办？**
A：程序已自动处理 PNG 透明背景转白底，无需手动操作。

**Q：中文路径是否支持？**
A：支持。所有路径处理使用 pathlib，兼容中文目录和中文文件名。

**Q：如何修改输出目录？**
A：在设置页面可以修改默认输出目录，或在各功能页面单独选择输出目录。

**Q：如何调整图片质量？**
A：在设置页面修改默认质量，或在各功能页面单独调整。默认 90。

**Q：打包后 exe 找不到怎么办？**
A：打包使用 one-folder 模式，exe 在 `dist\PDFImageConverter\PDFImageConverter.exe`。

---

## 后续可扩展功能

- PDF 水印添加
- PDF 页面旋转
- PDF 加密/解密
- 图片批量裁剪
- OCR 文字识别
- 多语言支持
- 主题切换（深色/浅色）
