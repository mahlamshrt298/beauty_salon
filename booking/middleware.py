class BookingFlowMiddleware:
    # میدلور مدیریت فلوی رزرو
    # کارش اینه که چک کنه کاربر کجای سایته و اگه از پروسه رزرو خارج شد، 
    # سشن‌های مربوط به رزرو (مثل تخفیف‌ها) رو دور بریزه که واسه رزروهای بعدی باگ نخوریم.

    def __init__(self, get_response):
        # متد استاندارد مقداردهی اولیه میدلور تو جنگو
        self.get_response = get_response

    def __call__(self, request):
        # این لیستِ تمام URL هایی هست که جزو مراحل رزرو حساب میشن
        booking_paths = [
            "/reserve/",
            "/select-date/",
            "/contact-info/",
            "/payment-confirm/",
        ]

        #آیا کاربر در حال حاضر درگیر مراحل رزرو هست؟
        in_booking_flow = request.session.get("in_booking_flow")

        # اگه کاربر وسط پروسه رزرو بود:
        if in_booking_flow:
            # چک می‌کنیم ببینیم مسیری که الان داره میره (request.path) جزو مسیرهای رزرو هست یا نه؟
            #حالا اگر نبود
            if not any(request.path.startswith(p) for p in booking_paths):
                #دیتای تخفیف و فلگ رزرو رو از سشن پاپ می‌کنیم
                request.session.pop("discount_id", None)
                request.session.pop("discounted_price", None)
                request.session.pop("in_booking_flow", None)

        # در نهایت ریکوئست رو پاس میدیم به لایه بعدی (یا ویو) که کارش رو بکنه
        return self.get_response(request)
