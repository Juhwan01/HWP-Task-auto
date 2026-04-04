"""OpenAI API 공통 엔진.

문서 생성용 프롬프트 호출과 톤앤매너 유지 시스템 프롬프트를 관리한다.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI


SYSTEM_PROMPT = """당신은 장애인 직업재활시설의 직업훈련교사입니다.
근로장애인의 직업재활 문서를 작성합니다.

중요한 규칙:
1. 톤앤매너: 제공된 전년도 원본 문서의 문체, 어미, 호칭, 표현 패턴을 완전히 동일하게 유지하세요.
2. "~함", "~보임", "~있음" 등의 어미가 원본에서 쓰였으면 그대로, "~하였습니다" 등 존대가 쓰였으면 그대로 따르세요.
3. 숫자/점수 표기 방식(예: "100점중 93점", "3점에서 4점으로")도 원본과 동일하게 유지하세요.
4. 구조와 항목 순서는 원본과 완전히 동일하게 유지하세요.
5. 달라지는 것은 오직 연도, 점수, 날짜 등 팩트(사실)만입니다.
6. 절대 새로운 표현이나 내용을 창작하지 마세요. 원본의 패턴을 따라가세요."""


class AiEngine:
    """OpenAI 기반 문서 내용 생성 엔진."""

    def __init__(self, env_path=None):
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o')

    def generate(self, user_prompt, temperature=0.3):
        """OpenAI API로 텍스트 생성.

        Args:
            user_prompt: 사용자 프롬프트
            temperature: 생성 온도 (낮을수록 보수적)

        Returns:
            생성된 텍스트
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content
