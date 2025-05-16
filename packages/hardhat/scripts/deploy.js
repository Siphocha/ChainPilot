const { ethers } = require("hardhat");
async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);
  const Token = await ethers.getContractFactory("Token");
  const token = await Token.deploy("Test Token", "TST");
  const tokenTx = await token.waitForDeployment();
  console.log("Token deployed to:", token.target, "Tx:", tokenTx.deploymentTransaction().hash);
  const agentWallet = "0x03B35d1f207395Fb4d7fDbcc44DE611A8f390184";
  await token.mint(agentWallet, ethers.parseUnits("1000", 6));
  console.log(`Minted 1000 tokens to ${agentWallet}`);
  const Executor = await ethers.getContractFactory("ChainPilotExecutor");
  const executor = await Executor.deploy();
  const executorTx = await executor.waitForDeployment();
  console.log("ChainPilotExecutor deployed to:", executor.target, "Tx:", executorTx.deploymentTransaction().hash);
  const Scheduler = await ethers.getContractFactory("ChainPilotScheduler");
  const scheduler = await Scheduler.deploy(executor.target);
  const schedulerTx = await scheduler.waitForDeployment();
  console.log("ChainPilotScheduler deployed to:", scheduler.target, "Tx:", schedulerTx.deploymentTransaction().hash);
}
main().then(() => process.exit(0)).catch((error) => { console.error(error); process.exit(1); });