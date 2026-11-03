#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用 Visio 把 .vsdx 渲染成 PNG —— 这是最权威的「Visio 实际怎么画」证据。
用法: python visio_export_png.py <vsdx路径> <输出png>
"""
import os
import sys
import time

import win32com.client


def export(vsdx_path, png_path, page_index=1):
    """Visio 未激活时 Export 常失败 → 多策略 + 多重试。"""
    for attempt in range(6):
        app = None
        try:
            app = win32com.client.DispatchEx("Visio.Application")
            app.Visible = False
            doc = app.Documents.OpenEx(vsdx_path, 2)
            page = doc.Pages.Item(page_index)

            if os.path.exists(png_path):
                os.remove(png_path)

            try:
                page.Export(png_path)
            except Exception:
                # 退路：整文档导出
                doc.Export(png_path)

            doc.Close()
            app.Quit()
            app = None
            if os.path.exists(png_path) and os.path.getsize(png_path) > 0:
                return os.path.getsize(png_path)
        except Exception as e:
            print(f"  尝试{attempt+1}: {str(e)[:80]}")
            time.sleep(3)
        finally:
            if app is not None:
                try:
                    app.Quit()
                except Exception:
                    pass
    return -1


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2]
    sz = export(src, dst)
    print(f"导出: {dst}  {sz} bytes")
