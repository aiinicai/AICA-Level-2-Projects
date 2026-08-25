using System.Security.Cryptography;
using Microsoft.AspNetCore.WebUtilities;

namespace Practice.Identity;

public static class SessionToken
{
    public static string Create()
    {
        Span<byte> bytes = stackalloc byte[32];
        RandomNumberGenerator.Fill(bytes);
        return WebEncoders.Base64UrlEncode(bytes);
    }

    public static byte[] Hash(string rawToken) => SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(rawToken));
}
