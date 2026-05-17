"""BaseBillingService — abstract contract for payment provider integrations."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from abc import ABC, abstractmethod

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class BaseBillingService(ABC):
    """Abstract billing provider. Swap implementations without touching orchestrator logic."""

    @abstractmethod
    async def create_checkout_session(
        self,
        customer_id: str | None,
        price_id: str,
        org_id: str,
        success_url: str,
        cancel_url: str,
    ) -> tuple[str, str]:
        """Create a checkout session and return (checkout_url, stripe_customer_id).

        Args:
            customer_id (str | None): Existing Stripe customer ID, or None to create one.
            price_id (str): Stripe price ID for the target plan.
            org_id (str): Org UUID as string — stored in Stripe metadata.
            success_url (str): Redirect URL on successful payment.
            cancel_url (str): Redirect URL on cancelled checkout.

        Returns:
            tuple[str, str]: (checkout_url, stripe_customer_id).

        """
        raise NotImplementedError("Subclasses must implement this method!")

    @abstractmethod
    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """Create a Stripe customer portal session URL.

        Args:
            customer_id (str): Stripe customer ID for the org.
            return_url (str): URL to return to after the portal session.

        Returns:
            str: Stripe portal session URL.

        """
        raise NotImplementedError("Subclasses must implement this method!")

    @abstractmethod
    async def parse_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Verify and parse a raw Stripe webhook payload.

        Args:
            payload (bytes): Raw request body from Stripe.
            sig_header (str): Value of the Stripe-Signature header.

        Raises:
            ValueError: If the signature is invalid or the payload cannot be parsed.

        Returns:
            dict: Parsed Stripe event dict.

        """
        raise NotImplementedError("Subclasses must implement this method!")

    @abstractmethod
    async def modify_subscription(self, stripe_sub_id: str, price_id: str) -> None:
        """Swap the price on an active subscription (immediate upgrade with proration).

        Args:
            stripe_sub_id (str): Stripe subscription ID to modify.
            price_id (str): New Stripe price ID for the target plan/period.

        """
        raise NotImplementedError("Subclasses must implement this method!")

    @abstractmethod
    async def cancel_subscription(self, stripe_sub_id: str) -> None:
        """Mark a subscription to cancel at the end of the current billing period.

        Args:
            stripe_sub_id (str): Stripe subscription ID to cancel.

        """
        raise NotImplementedError("Subclasses must implement this method!")
