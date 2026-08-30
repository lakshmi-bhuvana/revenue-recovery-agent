def generate_message(transaction, decision):
    """
    Generate a customer-facing recovery message
    based on the agent's decision.
    """

    channel = decision["recommended_channel"]
    action = decision["recovery_action"]

    amount = transaction["transaction_amount"]

    # -----------------------------------------
    # Action-specific message
    # -----------------------------------------

    if action == "payment_reminder":

        message = (
            f"Hi! We noticed that your payment of "
            f"₹{amount:,.2f} is still pending. "
            f"Please complete your payment to continue "
            f"your purchase. If you need any help, "
            f"we're happy to assist."
        )

    elif action == "retry_payment":

        message = (
            f"Hi! Your payment of ₹{amount:,.2f} "
            f"could not be completed. Please try "
            f"the payment again using your preferred "
            f"payment method."
        )

    elif action == "authentication_retry":

        message = (
            f"Hi! Your payment of ₹{amount:,.2f} "
            f"requires another authentication attempt. "
            f"Please retry the payment to complete "
            f"your transaction."
        )

    elif action == "checkout_reminder":

        message = (
            f"Hi! You were almost done with your "
            f"purchase of ₹{amount:,.2f}. "
            f"Complete your checkout whenever you're ready."
        )

    elif action == "subscription_reactivation":

        message = (
            f"Hi! Your subscription payment of "
            f"₹{amount:,.2f} needs attention. "
            f"Please update your payment details "
            f"to reactivate your subscription."
        )

    elif action == "mandate_reactivation":

        message = (
            f"Hi! Your recurring payment mandate "
            f"needs to be reactivated. Please complete "
            f"the required steps to continue your service."
        )

    else:

        message = (
            f"Hi! We noticed an issue with your "
            f"payment of ₹{amount:,.2f}. "
            f"Please review your payment and try again."
        )

    # -----------------------------------------
    # Channel-specific formatting
    # -----------------------------------------

    if channel == "sms":

        message = message

    elif channel == "whatsapp":

        message = message + (
            "\n\nReply to this message if you need help."
        )

    elif channel == "email":

        message = (
            "Subject: Action needed for your payment\n\n"
            + message
        )

    return {
        "channel": channel,
        "action": action,
        "message": message
    }


if __name__ == "__main__":

    test_transaction = {
        "transaction_amount": 22119.59
    }

    test_decision = {
        "recommended_channel": "sms",
        "recovery_action": "payment_reminder"
    }

    result = generate_message(
        test_transaction,
        test_decision
    )

    print("\n======================================")
    print("RECOVERY MESSAGE")
    print("======================================")

    print("Channel:", result["channel"])
    print("Action:", result["action"])
    print("\nMessage:")
    print(result["message"])