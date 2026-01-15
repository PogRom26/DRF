import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class CreateCoursePaymentAPIView(APIView):
    """Заглушка для создания платежа за курс через Stripe."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {
                "success": True,
                "message": "Stripe integration will be implemented here",
                "payment_url": "https://stripe.com/test",
            }
        )
