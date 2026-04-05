"""OpenAI API 공통 엔진.

Data-Grounded Generation 원칙(팩트 기반 서술, 보고서체 어미, 점수 표기 등)을
담은 시스템 프롬프트를 관리하고, 문서 생성용 프롬프트를 호출한다.
"""
import os
from dotenv import load_dotenv
from openai import OpenAI


SYSTEM_PROMPT = """당신은 장애인 직업재활시설의 직업훈련교사입니다.
근로장애인의 직업재활 문서를 작성합니다.

핵심 원칙 (Data-Grounded Generation):
1. 제공된 현장평가 팩트(점수, 항목별 강점/약점)만을 근거로 서술문을 새로 작성하세요.
2. 문체 규칙: "~함", "~보임", "~있음" 등 보고서체 어미를 사용하세요.
   회의록 발화체는 "~합니다", "~입니다" 등 존대어미를 사용하세요.
3. 점수 표기: "100점중 94점", "90점중 82점을 얻어 91%" 등 구체적 수치를 포함하세요.
4. 팩트에 없는 내용을 지어내지 마세요. 주어진 데이터만 분석하세요.
5. 이전 연도 문서를 그대로 베끼지 마세요. 올해 데이터를 바탕으로 새 문장을 쓰세요."""


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
