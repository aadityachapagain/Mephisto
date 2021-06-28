import {config as configDotenv} from 'dotenv'
import {resolve} from 'path'

switch(process.env.NODE_ENV) {
  case "development":
    console.log("Environment is 'development'")
    configDotenv({
      path: resolve(__dirname, "../.env.development")
    })
    break
  case "production":
    configDotenv({
      path: resolve(__dirname, "../.env.production")
    })
    break
  // Add 'staging' and 'production' cases here as well!
  default:
    throw new Error(`'NODE_ENV' ${process.env.NODE_ENV} is not handled!`)
}