# CareLink Jobs - Daycare Teaching Positions SPA

A Single Page Application (SPA) for teachers to find daycare jobs in Vancouver, Surrey, Langley, Abbotsford, Chilliwack, and surrounding areas.

## Features

- **Server-side Authentication**: Signup/login stored in SQLite with server verification
- **Guest Access**: Quick local guest sign-in for demos
- **Job Search**: Search across daycare names, roles, regions, schedules, and keywords
- **Regional Filtering**: Filter jobs by region with quick-access tabs
- **Job Type Filtering**: Filter by Full-time or Part-time positions
- **Pre-populated Data**: 32+ job listings across 15+ regions
- **Analytics Ready**: Event tracking infrastructure in place for future monetization

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn

### Installation

1. Navigate to the project directory:
```bash
cd playground/daycare-jobs-spa
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. In a second terminal, start the auth server:
```bash
npm run start:server
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Usage

1. **Login**: Create an account or sign in with your email and password, or continue as guest
2. **Browse Jobs**: View all available positions in the table
3. **Filter by Region**: Click region tabs or use the dropdown filter
4. **Filter by Type**: Use the job type dropdown to filter Full-time or Part-time
5. **Search**: Use the search box to find specific daycares, roles, or keywords
6. **Logout**: Click the logout button to clear your session

## Analytics Tracking

The application includes event tracking infrastructure that stores events in localStorage. Events tracked include:

- `login` - User login events
- `guest_login` - Guest access events
- `logout` - User logout events
- `dashboard_view` - Dashboard page views
- `search` - Search queries and results
- `filter_region` - Region filter changes
- `filter_type` - Job type filter changes
- `region_tab_click` - Region tab clicks

All events are stored in `localStorage` under the key `carelink-analytics` and can be exported for analysis or sent to an analytics service in the future.

## Project Structure

```
daycare-jobs-spa/
├── public/
│   └── index.html
├── server.js
├── src/
│   ├── components/
│   │   ├── Login.js
│   │   ├── Login.css
│   │   ├── Dashboard.js
│   │   └── Dashboard.css
│   ├── context/
│   │   └── AuthContext.js
│   ├── data/
│   │   └── jobsData.js
│   ├── App.js
│   ├── App.css
│   ├── index.js
│   └── index.css
├── package.json
└── README.md
```

## Future Enhancements

- Backend integration for real job data
- User profiles and saved jobs
- Email notifications for new positions
- Advanced analytics dashboard
- Monetization features (premium subscriptions, featured listings, etc.)

## Technologies Used

- React 18
- React Router DOM 6
- CSS3 (Custom properties, Grid, Flexbox)

## License

This project is for demonstration purposes.
