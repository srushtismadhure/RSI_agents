import random


def get_random_failure(target_env):
    if target_env == "simple-micro":
        return random.choice([
            "cpu-stress",
            "memory-stress",
            "pod-fail",
            "network-loss",
            "network-delay",
            "disk-io",
            "pod-config-error"
        ])
    elif target_env == "train-ticket":
        return random.choice([
            "cpu-stress",
            "memory-stress",
            "pod-fail",
            "network-loss",
            "network-delay",
            "disk-io",
            "pod-config-error"
        ])
    elif target_env == "online-boutique":
        return random.choice([
            "cpu-stress",
            "memory-stress",
            "pod-fail",
            "network-loss",
            "network-delay",
            "disk-io",
            "pod-config-error"
        ])


def get_random_service(target_env, failure_type):
    if target_env == "simple-micro":
        return random.choice(["hello-service", "time-service"])
    elif target_env == "train-ticket":
        if failure_type == "disk-io":
            return random.choice([
                "nacosdb-mysql"
            ])
        else:
            return random.choice([
                "ts-admin-basic-info-service",
                "ts-admin-order-service",
                "ts-admin-route-service",
                "ts-admin-travel-service",
                "ts-admin-user-service",
                "ts-assurance-service",
                "ts-auth-service",
                "ts-avatar-service",
                "ts-basic-service",
                "ts-cancel-service",
                "ts-config-service",
                "ts-consign-price-service",
                "ts-consign-service",
                "ts-contacts-service",
                "ts-delivery-service",
                "ts-execute-service",
                "ts-food-delivery-service",
                "ts-food-service",
                "ts-gateway-service",
                "ts-inside-payment-service",
                "ts-news-service",
                "ts-notification-service",
                "ts-order-other-service",
                "ts-order-service",
                "ts-payment-service",
                "ts-preserve-other-service",
                "ts-preserve-service",
                "ts-price-service",
                "ts-rebook-service",
                "ts-route-plan-service",
                "ts-route-service",
                "ts-seat-service",
                "ts-security-service",
                "ts-station-food-service",
                "ts-station-service",
                "ts-ticket-office-service",
                "ts-train-food-service",
                "ts-train-service",
                "ts-travel-plan-service",
                "ts-travel-service",
                "ts-travel2-service",
                "ts-ui-dashboard",
                "ts-user-service",
                "ts-verification-code-service",
                "ts-voucher-service",
                "ts-wait-order-service"
            ])
    elif target_env == "online-boutique":
        if failure_type == "disk-io":
            return random.choice([
                "adservice",
                "cartservice",
                "checkoutservice",
                "currencyservice",
                "emailservice",
                "frontend",
                "loadgenerator",
                "paymentservice",
                "productcatalogservice",
                "recommendationservice",
                "shippingservice"
            ])
        else:
            return random.choice([
                "adservice",
                "cartservice",
                "checkoutservice",
                "currencyservice",
                "emailservice",
                "frontend",
                "loadgenerator",
                "paymentservice",
                "productcatalogservice",
                "recommendationservice",
                "redis-cart",
                "shippingservice"
            ])
