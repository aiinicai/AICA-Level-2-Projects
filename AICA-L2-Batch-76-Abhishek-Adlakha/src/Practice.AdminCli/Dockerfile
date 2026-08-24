FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /source
COPY ["Directory.Build.props", "Directory.Packages.props", "."]
COPY ["src/Practice.BuildingBlocks/Practice.BuildingBlocks.csproj", "src/Practice.BuildingBlocks/"]
COPY ["src/Practice.Database/Practice.Database.csproj", "src/Practice.Database/"]
COPY ["src/Practice.Identity/Practice.Identity.csproj", "src/Practice.Identity/"]
COPY ["src/Practice.AdminCli/Practice.AdminCli.csproj", "src/Practice.AdminCli/"]
RUN dotnet restore "src/Practice.AdminCli/Practice.AdminCli.csproj"
COPY src/ src/
RUN dotnet publish "src/Practice.AdminCli/Practice.AdminCli.csproj" -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgssapi-krb5-2 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /app .
USER $APP_UID
ENTRYPOINT ["dotnet", "Practice.AdminCli.dll"]
