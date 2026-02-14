class BookingFlowMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        booking_paths = [
            "/reserve/",
            "/select-date/",
            "/contact-info/",
            "/payment-confirm/",
        ]

        in_booking_flow = request.session.get("in_booking_flow")

        if in_booking_flow:
            if not any(request.path.startswith(p) for p in booking_paths):
                request.session.pop("discount_id", None)
                request.session.pop("discounted_price", None)
                request.session.pop("in_booking_flow", None)

        return self.get_response(request)
