targetScope = 'resourceGroup'

@description('Primary deployment location for all resources.')
param location string = resourceGroup().location

@description('Short prefix used to build resource names.')
param appName string = 'aiarcdemo'

@secure()
@description('Administrator password for the Azure SQL logical server.')
param sqlAdminPassword string

var appServicePlanName = '${appName}-plan'
var webAppName = '${appName}-web'
var storageAccountName = toLower(replace('${appName}store', '-', ''))
var sqlServerName = '${appName}-sql'
var sqlDatabaseName = '${appName}-db'
var keyVaultName = '${appName}-kv'
var appInsightsName = '${appName}-appi'
var serviceBusName = '${appName}-sb'
var aiSearchName = '${appName}-search'
var openAiName = '${appName}-openai'

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
    size: 'B1'
    capacity: 1
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
    enabledForDeployment: true
    enabledForTemplateDeployment: true
  }
}

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: 'sqladminuser'
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: sqlDatabaseName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
    capacity: 5
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
  }
}

resource serviceBus 'Microsoft.ServiceBus/namespaces@2023-01-01-preview' = {
  name: serviceBusName
  location: location
  sku: {
    name: 'Basic'
    tier: 'Basic'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

resource aiSearch 'Microsoft.Search/searchServices@2023-11-01' = {
  name: aiSearchName
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    replicaCount: 1
    partitionCount: 1
  }
}

resource openAi 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAiName
    publicNetworkAccess: 'Enabled'
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'NODE|20-lts'
      appSettings: [
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'STORAGE_ACCOUNT_NAME'
          value: storageAccount.name
        }
        {
          name: 'SQL_SERVER_NAME'
          value: sqlServer.name
        }
        {
          name: 'SQL_DATABASE_NAME'
          value: sqlDatabase.name
        }
        {
          name: 'SERVICE_BUS_NAMESPACE'
          value: serviceBus.name
        }
        {
          name: 'KEY_VAULT_NAME'
          value: keyVault.name
        }
        {
          name: 'AZURE_OPENAI_NAME'
          value: openAi.name
        }
        {
          name: 'AI_SEARCH_NAME'
          value: aiSearch.name
        }
      ]
    }
  }
}

output deployedWebAppName string = webApp.name
output deployedSqlServerName string = sqlServer.name
output deployedStorageAccountName string = storageAccount.name