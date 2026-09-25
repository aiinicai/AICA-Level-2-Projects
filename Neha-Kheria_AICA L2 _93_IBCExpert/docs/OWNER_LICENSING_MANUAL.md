# IBC Expert — Owner Licensing Manual

## Security boundary
The customer package contains only the Ed25519 **public verification key**. The owner's **private signing key must never be copied into, bundled with, or distributed alongside the customer application**.

## One-time owner key creation
Use the separate utility under `owner_tools/licence_generator/` in the owner's controlled environment. Generate the signing key pair once and back up the private key securely. Never silently regenerate a lost/replaced key if previously issued licences must remain verifiable.

## Issuing an offline licence
1. Ask the customer for the **Device / Installation Request Code** shown by IBC Expert.
2. In the owner-only licence generator, enter/select the customer information, licence ID/type, start/expiry, device allowance and feature entitlements.
3. Bind to the supplied request code when device binding is required.
4. Generate the signed activation entitlement/credentials.
5. Send only the customer activation information/licence material; never send the private key.
6. The customer enters the credentials in IBC Expert. The application validates the signature and entitlement locally.

## Customer package build
Set `IBC_EXPERT_PUBLIC_KEY` to the correct 32-byte public verification key and use `scripts/build_windows.ps1`. The build verification script rejects owner-tool paths/private-key material and validates the embedded public key before release packaging.

## Licence replacement/renewal
Issue a new signed entitlement according to the commercial policy. Expiry/replacement must not delete or corrupt client data.
