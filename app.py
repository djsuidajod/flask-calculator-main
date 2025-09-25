from flask import Flask, render_template, request, redirect, url_for, flash
import re, math, requests

app = Flask(__name__)
app.secret_key = "change-this"   # flash 메시지에 사용할 임시 키

# --------------------------------------------------
# 수식 파서: 사칙연산(+,-,*,/)과 괄호 계산 지원
# --------------------------------------------------
def skip_spaces(expr):
    return expr.lstrip()

def parse_number(expr):
    expr = skip_spaces(expr)
    m = re.match(r'\d+(\.\d+)?', expr)
    if not m:
        raise ValueError("숫자가 필요합니다.")
    num = float(m.group())
    return num, expr[len(m.group()):]

def parse_factor(expr):
    expr = skip_spaces(expr)
    if expr.startswith('('):
        val, rest = parse_expression(expr[1:])
        rest = skip_spaces(rest)
        if not rest.startswith(')'):
            raise ValueError("')'가 필요합니다.")
        return val, rest[1:]
    return parse_number(expr)

def parse_term(expr):
    val, rest = parse_factor(expr)
    while True:
        rest = skip_spaces(rest)
        if rest.startswith('*'):
            nv, rest = parse_factor(rest[1:]); val *= nv
        elif rest.startswith('/'):
            nv, rest = parse_factor(rest[1:]); val /= nv
        else:
            break
    return val, rest

def parse_expression(expr):
    val, rest = parse_term(expr)
    while True:
        rest = skip_spaces(rest)
        if rest.startswith('+'):
            nv, rest = parse_term(rest[1:]); val += nv
        elif rest.startswith('-'):
            nv, rest = parse_term(rest[1:]); val -= nv
        else:
            break
    return val, rest

def calculate_expression(expr):
    val, rem = parse_expression(expr)
    if skip_spaces(rem):
        raise ValueError("잘못된 수식입니다.")
    return val

def calculate_scientific(expr):
    # math 모듈의 안전한 함수만 허용
    allowed = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
    code = compile(expr, "<string>", "eval")
    for name in code.co_names:
        if name not in allowed:
            raise NameError(f"허용되지 않은 함수: {name}")
    return eval(code, {"__builtins__": {}}, allowed)

# FastAPI 백엔드 주소 (Flask가 계산 결과를 전송할 대상)
API_URL = "http://127.0.0.1:8001"

# --------------------------------------------------
# 라우트
# --------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    try:
        resp_basic = requests.get(f"{API_URL}/history")
        rows_basic = resp_basic.json()
    except Exception as e:
        flash(f"일반 이력 조회 오류: {e}")
        rows_basic = []

    try:
        resp_sci = requests.get(f"{API_URL}/sci_history")
        rows_sci = resp_sci.json()
    except Exception as e:
        flash(f"공학 이력 조회 오류: {e}")
        rows_sci = []

    return render_template(
        "index.html",
        rows_basic=rows_basic,
        rows_sci=rows_sci
    )


@app.route("/calc", methods=["POST"])
def calc():
    expr = (request.form.get("expression") or "").strip()
    mode = request.form.get("mode", "basic")

    if not expr:
        flash("수식을 입력하세요.")
        return redirect(url_for("index"))

    try:
        if mode == "basic":
            
            result = calculate_expression(expr)
            requests.post(f"{API_URL}/calc",
                          json={"expression": expr, "result": result})
        elif mode == "sci":
            
            result = calculate_scientific(expr)
            requests.post(f"{API_URL}/sci_calc",
                          json={"expression": expr, "result": result})
        else:
            raise ValueError("잘못된 모드")
        flash(f"결과: {result:.6f}")
    except Exception as e:
        flash(f"오류: {e}")

    return redirect(url_for("index"))


# --------------------------------------------------
# 이력 초기화 라우트 (FastAPI DELETE 호출)
# --------------------------------------------------
@app.route("/history/clear", methods=["POST"])
def history_clear():
    try:
        r = requests.delete(f"{API_URL}/history")
        if r.status_code == 200:
            flash("일반 계산기 이력이 모두 삭제되었습니다.")
        else:
            flash("이력 삭제 실패")
    except Exception as e:
        flash(f"삭제 중 오류: {e}")
    return redirect(url_for("index"))

@app.route("/sci_history/clear", methods=["POST"])
def sci_history_clear():
    try:
        r = requests.delete(f"{API_URL}/sci_history")
        if r.status_code == 200:
            flash("공학 계산기 이력이 모두 삭제되었습니다.")
        else:
            flash("공학 이력 삭제 실패")
    except Exception as e:
        flash(f"삭제 중 오류: {e}")
    return redirect(url_for("index"))

# --------------------------------------------------
# 서버 시작
# --------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
