# gyerori

디자인과 기획 사이에서 보고, 고민하고, 배운 것을 기록합니다.

블로그: https://gyerori.github.io

## 글과 소개

- `content/posts/`: 공개가 승인된 Markdown 원고만 보관합니다.
- `content/about.html`: 소개 문구입니다.
- `assets/site.css`: 블로그 디자인입니다.
- `site.json`: 사이트 이름·주소·소개를 관리합니다.

이 저장소와 모든 커밋 이력은 공개됩니다. 비공개 초안·글감·개인 메모·인증 정보는 저장하지 않습니다.

## 로컬 확인

Python 3.12 이상에서 실행합니다.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/build.py
python -m http.server 8000 --directory _site --bind 127.0.0.1
```

`main`의 변경 사항은 GitHub Actions에서 테스트·빌드 후 GitHub Pages로 배포됩니다. 자동화에는 GitHub가 제공하는 저장소 한정 토큰을 사용하며, 개인 토큰을 저장소에 넣지 않습니다.
