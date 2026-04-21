import json
import asyncio
import os
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def generate_qa_from_text(text: str, num_pairs: int = 5) -> List[Dict]:
    """
    Sử dụng OpenAI API để tạo các cặp (Question, Expected Answer, Context)
    từ đoạn văn bản cho trước.
    Yêu cầu: Tạo ít nhất 1 câu hỏi 'lừa' (adversarial) hoặc cực khó.
    """
    print(f"Generating {num_pairs} QA pairs from text...")
    
    prompt = f"""Từ đoạn văn bản sau, hãy tạo {num_pairs} cặp câu hỏi-trả lời (Q&A) bằng tiếng Việt.
    
Yêu cầu:
- Tạo {num_pairs - 1} câu hỏi thông thường (easy/medium difficulty)
- Tạo 1 câu hỏi 'lừa' (adversarial) hoặc cực khó (hard difficulty) - câu hỏi này có thể dựa trên suy luận sai lệm hoặc chi tiết tinh tế
- Mỗi câu hỏi phải có câu trả lời chi tiết dựa trên nội dung
- Trả về kết quả dưới dạng JSON array

Đoạn văn bản:
{text}

Trả về JSON array với cấu trúc:
[
  {{
    "question": "...",
    "expected_answer": "...",
    "difficulty": "easy|medium|hard",
    "type": "fact-check|reasoning|adversarial"
  }},
  ...
]

Chỉ trả về JSON, không có text khác."""

    message = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = message.choices[0].message.content
    
    # Clean up markdown code blocks if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    try:
        qa_pairs = json.loads(response_text)
    except json.JSONDecodeError as e:
        # Fallback if JSON parsing fails
        print(f"Warning: Could not parse LLM response as JSON: {e}")
        print(f"Response preview: {response_text[:200]}")
        qa_pairs = [
            {
                "question": "Câu hỏi mẫu từ tài liệu?",
                "expected_answer": "Câu trả lời kỳ vọng mẫu.",
                "difficulty": "easy",
                "type": "fact-check"
            }
        ]
    
    # Add context to each pair
    for pair in qa_pairs:
        pair["context"] = text[:500]
        if "metadata" not in pair:
            pair["metadata"] = {
                "difficulty": pair.get("difficulty", "medium"),
                "type": pair.get("type", "fact-check")
            }
    
    return qa_pairs

async def main():
    # Read the two documents
    # Read the two documents
    with open("data/docs/policy_refund_v4.txt", "r", encoding="utf-8") as f:
        refund_text = f.read()
    
    with open("data/docs/sla_p1_2026.txt", "r", encoding="utf-8") as f:
        sla_text = f.read()

    with open("data/docs/access_control_sop.txt", "r", encoding="utf-8") as f:
        sop_text = f.read()
    
    with open("data/docs/hr_leave_policy.txt", "r", encoding="utf-8") as f:
        hr_leave_text = f.read()
    
    with open("data/docs/it_helpdesk_faq.txt", "r", encoding="utf-8") as f:
        it_helpdesk_text = f.read()

    # Generate 10 Q&A pairs from each document
    print("Generating Q&A pairs from access_control_sop.txt...")
    sop_qa = await generate_qa_from_text(sop_text, num_pairs=10)
    
    print("Generating Q&A pairs from hr_leave_policy.txt...")
    hr_qa = await generate_qa_from_text(hr_leave_text, num_pairs=10)
    
    print("Generating Q&A pairs from it_helpdesk_faq.txt...")
    it_qa = await generate_qa_from_text(it_helpdesk_text, num_pairs=10)

    # Generate 10 Q&A pairs from each document
    print("Generating Q&A pairs from policy_refund_v4.txt...")
    refund_qa = await generate_qa_from_text(refund_text, num_pairs=10)
    
    print("Generating Q&A pairs from sla_p1_2026.txt...")
    sla_qa = await generate_qa_from_text(sla_text, num_pairs=10)

    # Combine and save to golden_set.jsonl
    all_qa = sop_qa + hr_qa + it_qa + refund_qa + sla_qa
    
    with open("data/golden_set.jsonl", "w", encoding="utf-8") as f:
        for pair in all_qa:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    
    print(f"Done! Generated {len(all_qa)} Q&A pairs and saved to data/golden_set.jsonl")

if __name__ == "__main__":
    asyncio.run(main())
