from groq import Groq
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.models.chat import ChatMessage
from app.services import market_data_service, behavioral_finance_service, nlp_sentiment_service
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

# Modelin kapasitesi: Llama 3.3 70B - 128K token. Biz kullanıcı başına son 10 mesajı tutacağız.
MAX_HISTORY_MESSAGES = 10


def build_user_context(db: Session, user_id: int) -> str:
    """
    RAG (Retrieval-Augmented Generation) - kullanıcının kişisel verisini
    sistem prompt'una dahil etmek için bağlam oluşturur.

    Şunları çeker:
    1. Kullanıcı bilgileri (isim, bakiye)
    2. Portföy pozisyonları (güncel fiyat ve PnL ile)
    3. Son 5 işlem
    4. Davranışsal finans profili (varsa)
    5. Son haberler (sentiment ile)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return "Kullanıcı bulunamadı."

    # 1. Portföy
    holdings = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    portfolio_lines = []
    total_value = 0.0
    total_cost = 0.0

    for h in holdings:
        try:
            md = market_data_service.get_stock_data(h.symbol)
            cp = md["current_price"]
            cost = h.average_cost * h.quantity
            val = cp * h.quantity
            total_cost += cost
            total_value += val
            pnl = val - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0
            portfolio_lines.append(
                f"- {h.symbol}: {h.quantity:.0f} lot, "
                f"maliyet ₺{h.average_cost:.2f}, güncel ₺{cp:.2f}, "
                f"PnL: {pnl:+.2f} TL ({pnl_pct:+.2f}%)"
            )
        except Exception:
            portfolio_lines.append(
                f"- {h.symbol}: {h.quantity:.0f} lot, maliyet ₺{h.average_cost:.2f} (güncel fiyat alınamadı)"
            )

    portfolio_text = "\n".join(portfolio_lines) if portfolio_lines else "Henüz hisse pozisyonu yok, tüm varlık nakit."
    total_pnl = total_value - total_cost

    # 2. Son 5 işlem
    recent_txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.timestamp.desc())
        .limit(5)
        .all()
    )
    tx_lines = []
    for tx in recent_txs:
        date_str = tx.timestamp.strftime("%d %B").replace(
            "January", "Ocak").replace("February", "Şubat").replace("March", "Mart") \
            .replace("April", "Nisan").replace("May", "Mayıs").replace("June", "Haziran") \
            .replace("July", "Temmuz").replace("August", "Ağustos").replace("September", "Eylül") \
            .replace("October", "Ekim").replace("November", "Kasım").replace("December", "Aralık")
        action = "ALIŞ" if tx.transaction_type == "BUY" else "SATIŞ"
        tx_lines.append(f"- {date_str}: {action} {tx.symbol} {tx.quantity:.0f} lot @ ₺{tx.price:.2f}")
    tx_text = "\n".join(tx_lines) if tx_lines else "Henüz işlem yok."

    # 3. Davranışsal profil
    behavior = behavioral_finance_service.analyze_user_behavior(db, user_id)
    if behavior.get("has_enough_data"):
        persona = behavior["persona"]
        de = behavior["disposition_effect"]["score"]
        oc = behavior["overconfidence"]["score"]
        la = behavior["loss_aversion"]["score"]
        behavior_text = (
            f"Yatırımcı tipi: {persona['title']} - {persona['description']}\n"
            f"Disposition Effect (kazancı erken satma): {de} / 1.00\n"
            f"Overconfidence (aşırı işlem): {oc} / 1.00\n"
            f"Loss Aversion (zarardan kaçınma): {la} / 1.00"
        )
    else:
        behavior_text = "Davranışsal profil için yeterli veri yok (en az 3 işlem gerekli)."

    # 4. Son haberler (cache'den al, sentiment ile)
    try:
        news = nlp_sentiment_service.get_financial_news("stocks market")[:3]
        news_text = "\n".join([
            f"- [{n['sentiment_label']}] {n['title'][:120]}"
            for n in news
        ])
    except Exception:
        news_text = "Haber verisi alınamadı."

    # Context'i birleştir
    context = f"""KULLANICI BİLGİLERİ:
İsim: {user.full_name or 'Kullanıcı'}
Nakit Bakiye: ₺{user.balance:,.2f}
Toplam Hisse Değeri: ₺{total_value:,.2f}
Toplam Varlık: ₺{(user.balance + total_value):,.2f}
Toplam PnL: {total_pnl:+,.2f} TL

PORTFÖY:
{portfolio_text}

SON İŞLEMLER:
{tx_text}

DAVRANIŞSAL FİNANS PROFİLİ:
{behavior_text}

GÜNCEL PİYASA HABERLERİ:
{news_text}"""

    return context


def get_system_prompt(user_context: str) -> str:
    """
    Sistem prompt'u - AI'ın nasıl davranacağını belirler.
    Guardrail'ler ve dil kuralları burada.
    """
    return f"""Sen Portly adlı sanal borsa eğitim uygulamasının Türk AI finansal koçusun.

KESİN DİL KURALI: Cevabının %100'ü Türkçe olacak. İngilizce tek bir kelime bile kullanma.
Şirket isimleri (Apple, Tesla) ve sembol isimleri (THYAO.IS, AAPL) aynen kalır.

ÖNEMLİ KURALLAR:
1. ASLA yatırım tavsiyesi verme. "Al", "sat" gibi kesin yönlendirmeler yapma.
2. Eğitici ol — kavramları açıkla, akademik referans ver (Kahneman, Markowitz, Shefrin gibi).
3. Kullanıcının verisine dayalı kişisel cevap ver. Generic cevap verme.
4. Cevaplar 2-4 paragraf, sade dil, markdown formatlamasından uzak dur.
5. Emoji kullanma, gereksiz süslemelerden kaçın.
6. Davranışsal önyargıları (Disposition Effect, Loss Aversion, Overconfidence) gördüğünde nazikçe işaret et.
7. Eğer kullanıcı bilmediğin bir şey sorarsa "bu konuda kesin bilgim yok" de, uydurma.

KULLANICININ MEVCUT DURUMU:
{user_context}

Yukarıdaki verilere dayanarak kullanıcının sorularını yanıtla. Kullanıcıyı tanıyorsun gibi, kişisel ve sıcak bir tonla yaz."""


def save_message(db: Session, user_id: int, role: str, content: str) -> ChatMessage:
    """Mesajı DB'ye kaydet."""
    msg = ChatMessage(user_id=user_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_chat_history(db: Session, user_id: int, limit: int = 50) -> list:
    """Kullanıcının sohbet geçmişini döndür (kronolojik sırayla)."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.timestamp.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
        }
        for m in messages
    ]


def clear_chat_history(db: Session, user_id: int) -> int:
    """Kullanıcının tüm sohbet geçmişini sil. Silinen mesaj sayısını döndürür."""
    count = db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.commit()
    return count


def get_recent_messages_for_context(db: Session, user_id: int, limit: int = MAX_HISTORY_MESSAGES) -> list:
    """
    Son N mesajı LLM'e bağlam olarak göndermek için al.
    Llama'nın beklediği {role, content} formatında döndürür.
    """
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.timestamp.desc())
        .limit(limit)
        .all()
    )
    # Tersine çevir (chronological)
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


def stream_chat_response(db: Session, user_id: int, user_message: str):
    """
    Streaming generator - Llama'dan token-by-token cevap alıp yield eder.
    Aynı zamanda kullanıcı mesajını ve tam cevabı DB'ye kaydeder.

    Yield edilen formatın kendisi: SSE event verisi.
    """
    # 1. Kullanıcı mesajını DB'ye kaydet
    save_message(db, user_id, "user", user_message)

    # 2. RAG: kullanıcının güncel verilerini topla
    user_context = build_user_context(db, user_id)
    system_prompt = get_system_prompt(user_context)

    # 3. Sohbet geçmişini al (yeni eklediğimiz user message'ı dahil)
    history = get_recent_messages_for_context(db, user_id, MAX_HISTORY_MESSAGES)

    # 4. LLM'e gönderilecek mesajları hazırla
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    # 5. Streaming çağrı
    full_response = ""
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=800,
            temperature=0.4,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                token = delta.content
                full_response += token
                yield token

    except Exception as e:
        error_msg = f"\n\n[Hata: AI yanıt veremedi - {str(e)}]"
        full_response += error_msg
        yield error_msg

    # 6. Tam cevabı DB'ye kaydet
    if full_response.strip():
        save_message(db, user_id, "assistant", full_response.strip())