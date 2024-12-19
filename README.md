# Call Center Demo

A modern call center management system that demonstrates efficient call routing, agent management, and customer service capabilities.

## Key Features

- Intelligent call routing and queue management
- Real-time agent dashboard
- Customer interaction tracking
- Performance analytics and reporting
- CRM integration
- Automated call distribution (ACD)

## Technology Stack

- Frontend: React.js
- Backend: Node.js / Express
- Database: MongoDB
- WebRTC: Twilio
- Real-time: Socket.io

## Getting Started

### Prerequisites

- Node.js v14.x or later
- MongoDB v4.4 or later
- Twilio account and API credentials
- NPM or Yarn

### Installation

```bash
# Clone the repository
git clone https://github.com/odog96/call-center-demo.git

# Install dependencies
cd call-center-demo
npm install

# Set up environment variables
cp .env.example .env
```

### Configuration

1. Update `.env` with:
   - MongoDB URL
   - Twilio credentials
   - Application port
2. Configure WebRTC settings
3. Set up agent profiles

## Development

```bash
# Start backend server
npm run server

# Start frontend development server
npm run client
```

## Testing

```bash
# Run tests
npm test

# Run linter
npm run lint
```

## Documentation

Detailed documentation is available in the [docs](./docs) directory:

- API Documentation
- Deployment Guide
- User Manual
- Administrator Guide

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.