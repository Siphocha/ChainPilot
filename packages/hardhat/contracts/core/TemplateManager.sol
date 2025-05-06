// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title ChainPilot - Template Manager
 * @notice Stores reusable task templates (e.g., multi-send, DAO voting scripts).
 * @dev Templates are gas-optimized for batch operations and can be cloned by users.
 */
contract TemplateManager {
    // ------------------------ Custom Errors ------------------------
    error Unauthorized();
    error InvalidTemplate();
    error TemplateLocked();

    // ------------------------ Structs & Events ------------------------
    struct Template {
        address owner;
        address target;
        bytes payload;  // Encoded function call (e.g., "send 0.1 ETH to A, B, C")
        bool isPublic;
        bool isLocked;  // Immutable once locked
    }

    event TemplateCreated(uint256 indexed templateId, address indexed owner);
    event TemplateUsed(uint256 indexed templateId, address indexed user);

    // ------------------------ Storage ------------------------
    mapping(uint256 => Template) public templates;
    uint256 public templateIdCounter;

    // ------------------------ External Functions ------------------------
    /**
     * @notice Create a new template.
     * @param target Contract to interact with (e.g., Executer.sol).
     * @param payload Encoded batch operation (use ABI.encodePacked for arrays).
     * @param isPublic If true, anyone can use this template.
     */
    function createTemplate(
        address target,
        bytes calldata payload,
        bool isPublic
    ) external returns (uint256 templateId) {
        if (target == address(0) || payload.length == 0) revert InvalidTemplate();

        templateId = templateIdCounter++;
        templates[templateId] = Template(msg.sender, target, payload, isPublic, false);

        emit TemplateCreated(templateId, msg.sender);
    }

    /**
     * @notice Lock a template (makes it immutable).
     * @dev Only the owner can lock.
     */
    function lockTemplate(uint256 templateId) external {
        Template storage template = templates[templateId];
        if (template.owner != msg.sender) revert Unauthorized();
        template.isLocked = true;
    }

    // ------------------------ Template Execution ------------------------
    /**
     * @notice Use a template to execute a batch task.
     * @dev Calls the pre-defined payload via Executer.sol.
     */
    function useTemplate(uint256 templateId) external {
        Template memory template = templates[templateId];
        if (!template.isPublic && template.owner != msg.sender) revert Unauthorized();

        (bool success, ) = template.target.call(template.payload);
        if (!success) revert ExecutionFailed();

        emit TemplateUsed(templateId, msg.sender);
    }
}