from groq import Groq
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.portfolio import Portfolio
from app.services import market_data_service, nlp_sentiment_service
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


def generate_portfolio_advice(db: Session, user_id: int) -> dict:
    """Kullanıcının portföyünü, PnL'ini ve güncel haber sentiment'ını analiz edip 
    Türkçe kişisel yorum üretir. Llama 3.3 70B kullanır."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": "Kullanıcı bulunamadı"}

    holdings = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

    # Portföy bilgilerini güncel fiyatlarla zenginleştir
    portfolio_summary = []
    total_cost = 0.0
    total_value = 0.0
    for h in holdings:
        try:
            market = market_data_service.get_stock_data(h.symbol)
            cp = market["current_price"]
            cost = h.average_cost * h.quantity
            val = cp * h.quantity
            total_cost += cost
            total_value += val
            portfolio_summary.append({
                "symbol": h.symbol,
                "quantity": h.quantity,
                "avg_cost": round(h.average_cost, 2),
                "current_price": round(cp, 2),
                "pnl": round(val - cost, 2),
                "pnl_percent": round(((val - cost) / cost * 100) if cost > 0 else 0, 2),
            })
        except Exception:
            continue

    total_pnl = total_value - total_cost

    # Son haberleri sentiment'la birlikte al
    try:
        news = nlp_sentiment_service.get_financial_news("stocks market")[:5]
    except Exception:
        news = []

    portfolio_text = "\n".join([
        f"- {p['symbol']}: {p['quantity']:.0f} lot, maliyet ₺{p['avg_cost']}, "
        f"güncel ₺{p['current_price']}, PnL: {p['pnl']:+} TL ({p['pnl_percent']:+}%)"
        for p in portfolio_summary
    ]) if portfolio_summary else "Hiç hisse yok, tüm varlık nakit."

    news_text = "\n".join([
        f"- [{n['sentiment_label']}] {n['title']}"
        for n in news
    ]) if news else "Haber verisi yok."

    prompt = f"""Sen Portly adlı sanal borsa eğitim uygulamasının Türk AI finansal koçusun.

KESIN DİL KURALI: Cevabının %100'ü Türkçe olacak. İngilizce tek bir kelime bile KULLANMA.
- "especially" → "özellikle"
- "stocks" → "hisseler"  
- "portfolio" → "portföy"
- Şirket isimleri aynen kalır (Apple, Tesla, Türk Hava Yolları)
- Sembol isimleri aynen kalır (THYAO.IS, AAPL)
- Başka TÜM kelimeler Türkçe olmalı

Yatırım tavsiyesi VERME, sadece eğitici gözlemler yap.

KULLANICININ SANAL PORTFÖYÜ:
Nakit Bakiye: ₺{user.balance:.2f}
Toplam Hisse Değeri: ₺{total_value:.2f}
Toplam Kâr/Zarar: {total_pnl:+.2f} TL

Hisseler:
{portfolio_text}

GÜNCEL PİYASA HABERLERİ (VADER sentiment analizi ile):
{news_text}

GÖREVİN (hepsi Türkçe, akıcı dille):
1. Portföy yapısını yorumla (çeşitlendirme, konsantrasyon, sektör riski)
2. Haberlerdeki genel duygu durumunu kullanıcının pozisyonlarıyla ilişkilendir
3. Eğitici bir kavram veya soruyla bitir

Format: 3-4 kısa paragraf, markdown yok, emoji yok, 120-180 kelime arası, TAMAMI TÜRKÇE."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.3,
        )
        advice = response.choices[0].message.content.strip()
        return {
            "advice": advice,
            "portfolio_size": len(portfolio_summary),
            "total_pnl": round(total_pnl, 2),
            "total_value": round(total_value, 2),
            "news_analyzed": len(news),
        }
    except Exception as e:
        return {"error": f"AI yanıt vermedi: {str(e)}"}