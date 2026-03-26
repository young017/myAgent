from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Iterable
import urllib.parse
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import requests


def _is_ip_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return (
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _resolve_host_ips(host: str) -> Iterable[str]:
    # SSRF 방지를 위해 호스트를 IP로 해석합니다.
    # DNS 해석 실패 시, 안전하게 차단 처리합니다.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return []

    ips: set[str] = set()
    for family, _, _, _, sockaddr in infos:
        # sockaddr가 (ip, port) 형태라고 가정
        ip = sockaddr[0]
        ips.add(ip)
    return ips


def _html_to_text(html: str) -> str:
    # 간단한 HTML -> 텍스트 변환(외부 의존성 없이).
    # 스크립트/스타일 제거 후 태그 제거, 연속 공백 정리.
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+\n", "\n\n", text)
    return text.strip()


@dataclass(frozen=True)
class WebToolkit:
    def fetch_url(self, *, url: str, timeout_s: int, max_chars: int) -> str:
        """
        인터넷에서 URL 내용을 가져와 텍스트로 반환합니다.
        - http/https만 허용
        - localhost/사설망 IP는 차단(SSRF 방지)
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("http/https URL만 허용됩니다.")

        host = parsed.hostname
        if not host:
            raise ValueError("호스트를 확인할 수 없는 URL입니다.")

        ips = _resolve_host_ips(host)
        if not ips:
            raise ValueError("호스트 IP 해석 실패 또는 차단되었습니다.")
        for ip in ips:
            if _is_ip_blocked(ip):
                raise ValueError("로컬/사설망으로의 접근은 차단됩니다.")

        headers = {"User-Agent": "myAgent-web-tool/0.1"}
        resp = requests.get(url, headers=headers, timeout=timeout_s)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        body = resp.text
        if "application/json" in content_type:
            # JSON이면 그대로 반환(모델이 파싱 가능)
            out = body
        else:
            out = _html_to_text(body)

        if max_chars and len(out) > max_chars:
            out = out[:max_chars]
        return out

    def search_namu(self, *, keyword: str, timeout_s: int, max_chars: int) -> str:
        """
        나무위키(namu.wiki)에서 정해진 키워드의 문서 페이지 본문을 가져와 텍스트로 반환합니다.
        """
        encoded = urllib.parse.quote(keyword)
        url = f"https://namu.wiki/w/{encoded}"
        
        # 봇 차단을 우회하기 위한 기본적인 브라우저 User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36: myAgent-bot/0.1"
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=timeout_s)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 404:
                return f"'{keyword}'에 대한 나무위키 문서를 찾을 수 없습니다 (404 Not Found)."
            else:
                raise e
                
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # CSS 스타일 및 자바스크립트 태그 내용 제외
        for element in soup(["script", "style"]):
            element.extract()
            
        # 띄어쓰기를 기준으로 텍스트 추출 (태그 간 공백 유지)
        extract_text = soup.get_text(separator=' ', strip=True)
        
        # 다중 공백 및 줄바꿈을 하나의 공백으로 압축하여 토큰 절약
        import re
        out = re.sub(r'\s+', ' ', extract_text).strip()
        
        if max_chars and len(out) > max_chars:
            out = out[:max_chars]
        return out


