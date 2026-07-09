from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import AccessVerifySerializer
from .services import AccessValidationService

class AccessVerifyView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AccessVerifySerializer(data=request.data)
        if serializer.is_valid():
            card_uid = serializer.validated_data['card_uid']
            device_id = serializer.validated_data['device_id']
            
            result = AccessValidationService.validate_scan(
                card_uid=card_uid,
                device_id=device_id
            )
            
            if result["authorized"]:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_403_FORBIDDEN)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
