import re
from typing import Optional
from urllib.parse import urlparse


class HTMLParser:
    @staticmethod
    def extract(html: str, url: str) -> dict:
        title = ""
        m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()

        description = ""
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if m:
            description = m.group(1).strip()
        if not description:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
            if m:
                description = m.group(1).strip()

        content = HTMLParser._extract_text(html)

        tags = []
        m = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if m:
            tags = [t.strip() for t in m.group(1).split(",")]

        return {
            "title": title,
            "description": description,
            "content": content[:10000],
            "tags": tags,
            "url": url,
            "domain": urlparse(url).netloc,
        }

    @staticmethod
    def _extract_text(html: str) -> str:
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 40]
        return "\n".join(lines)

    @staticmethod
    def extract_code_blocks(text: str) -> list:
        blocks = []
        for m in re.finditer(r'```(\w*)\n(.*?)```', text, re.DOTALL):
            blocks.append({"language": m.group(1), "code": m.group(2).strip()})
        for m in re.finditer(r'(?<!`)`([^`]+)`(?!`)', text):
            code = m.group(1).strip()
            if len(code) > 20 and "\n" not in code:
                blocks.append({"language": "", "code": code})
        return blocks

    @staticmethod
    def guess_language(text: str) -> Optional[str]:
        keywords = {
            "python": ["def ", "import ", "class ", "print(", "if __name__", "lambda ", "yield ", "async def"],
            "javascript": ["function ", "const ", "let ", "var ", "=>", "console.log", "document.", "export "],
            "typescript": [": string", ": number", ": void", "interface ", "type ", "as const"],
            "rust": ["fn ", "let mut", "impl ", "pub ", "unsafe ", "match ", "crate::"],
            "go": ["func ", "package ", "import (", "defer ", "go "],
            "java": ["public class", "private ", "void ", "static ", "System.out"],
            "cpp": ["#include", "std::", "template", "int main"],
            "bash": ["#!/bin", "sudo ", "apt ", "npm ", "pip ", "cargo "],
        }
        for lang, kws in keywords.items():
            if any(kw in text for kw in kws):
                return lang
        return None
