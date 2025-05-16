const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const walletAddress = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266";
  const tokenAddress = "0x5FbDB2315678afecb367f032d93F642f64180aa3"; // From config.py

  const Token = await hre.ethers.getContractAt("Token", tokenAddress, deployer);
  const decimals = await Token.decimals();
  const amount = hre.ethers.parseUnits("1000", decimals); // Mint 1000 tokens

  console.log(`Minting 1000 tokens to ${walletAddress}...`);
  const tx = await Token.mint(walletAddress, amount);
  await tx.wait();

  const balance = await Token.balanceOf(walletAddress);
  console.log(`New balance of ${walletAddress}: ${hre.ethers.formatUnits(balance, decimals)} tokens`);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });