// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// DA-1 Question 2 (unchanged) - 23BKT0045 / AKHYA SINHA
// Wallet-based digital identity registry. In DA-8 this contract is reused as the
// identity layer that CertificateRegistry consults before authorising an issuer.
contract DigitalIdentity {
    struct User {
        uint256 userId;
        string name;
        string department;
        bool isRegistered;
    }

    mapping(address => User) private users;
    uint256 public totalRegisteredUsers;

    event UserRegistered(address indexed walletAddress, uint256 userId, string name, string department);

    function registerUser(uint256 _userId, string memory _name, string memory _department) public {
        require(_userId > 0, "Error: User ID must be greater than zero.");
        require(!users[msg.sender].isRegistered, "Error: Wallet address is already registered.");

        users[msg.sender] = User({
            userId: _userId,
            name: _name,
            department: _department,
            isRegistered: true
        });

        totalRegisteredUsers++;
        emit UserRegistered(msg.sender, _userId, _name, _department);
    }

    function getUser(address _walletAddress)
        public
        view
        returns (
            uint256 userId,
            string memory name,
            string memory department
        )
    {
        require(users[_walletAddress].isRegistered, "Error: User is not registered.");
        User memory user = users[_walletAddress];
        return (user.userId, user.name, user.department);
    }

    function isWalletRegistered(address _walletAddress) public view returns (bool) {
        return users[_walletAddress].isRegistered;
    }
}
