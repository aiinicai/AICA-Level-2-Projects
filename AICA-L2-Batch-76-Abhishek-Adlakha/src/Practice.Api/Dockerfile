FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /source
COPY ["Directory.Build.props", "Directory.Packages.props", "."]
COPY ["src/Practice.BuildingBlocks/Practice.BuildingBlocks.csproj", "src/Practice.BuildingBlocks/"]
COPY ["src/Practice.Billing/Practice.Billing.csproj", "src/Practice.Billing/"]
COPY ["src/Practice.Database/Practice.Database.csproj", "src/Practice.Database/"]
COPY ["src/Practice.Identity/Practice.Identity.csproj", "src/Practice.Identity/"]
COPY ["src/Practice.Reporting/Practice.Reporting.csproj", "src/Practice.Reporting/"]
COPY ["src/Practice.Scheduling/Practice.Scheduling.csproj", "src/Practice.Scheduling/"]
COPY ["src/Practice.Api/Practice.Api.csproj", "src/Practice.Api/"]
RUN dotnet restore "src/Practice.Api/Practice.Api.csproj"
COPY src/ src/
RUN dotnet publish "src/Practice.Api/Practice.Api.csproj" -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /keys \
    && chown $APP_UID:$APP_UID /keys
COPY --from=build /app .
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet", "Practice.Api.dll"]
