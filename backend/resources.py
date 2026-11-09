"""
resources.py
Curated free learning resources (YouTube + well-known free sites) for each
skill in ranker.COMMON_SKILLS. Static and hand-picked rather than pulled from
a live API — this keeps the feature fast, free, and never broken by API
quota/key issues, which matters for a live demo.

Each skill maps to a short list of {title, url, type}.
"""

SKILL_RESOURCES = {
    "python": [
        {"title": "Python Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=rfscVS0vtbw", "type": "YouTube"},
        {"title": "Official Python Tutorial", "url": "https://docs.python.org/3/tutorial/", "type": "Docs"},
    ],
    "java": [
        {"title": "Java Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=xk4_1vDrzzo", "type": "YouTube"},
        {"title": "Java Tutorial (W3Schools)", "url": "https://www.w3schools.com/java/", "type": "Free site"},
    ],
    "javascript": [
        {"title": "JavaScript Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=PkZNo7MFNFg", "type": "YouTube"},
        {"title": "JavaScript.info", "url": "https://javascript.info/", "type": "Free site"},
    ],
    "typescript": [
        {"title": "TypeScript Course for Beginners", "url": "https://www.youtube.com/watch?v=d56mG7DezGs", "type": "YouTube"},
        {"title": "TypeScript Handbook", "url": "https://www.typescriptlang.org/docs/handbook/intro.html", "type": "Docs"},
    ],
    "c++": [
        {"title": "C++ Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=8jLOx1hD3_o", "type": "YouTube"},
        {"title": "learncpp.com", "url": "https://www.learncpp.com/", "type": "Free site"},
    ],
    "c#": [
        {"title": "C# Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=GhQdlIFylQ8", "type": "YouTube"},
        {"title": "Microsoft Learn: C#", "url": "https://learn.microsoft.com/en-us/dotnet/csharp/", "type": "Docs"},
    ],
    "sql": [
        {"title": "SQL Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=HXV3zeQKqGY", "type": "YouTube"},
        {"title": "SQLBolt (interactive)", "url": "https://sqlbolt.com/", "type": "Free site"},
    ],
    "nosql": [
        {"title": "NoSQL Databases Explained", "url": "https://www.youtube.com/watch?v=0buKQHokLK8", "type": "YouTube"},
        {"title": "MongoDB Free Course", "url": "https://university.mongodb.com/", "type": "Free site"},
    ],
    "react": [
        {"title": "React Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=bMknfKXIFA8", "type": "YouTube"},
        {"title": "Official React Docs", "url": "https://react.dev/learn", "type": "Docs"},
    ],
    "angular": [
        {"title": "Angular Full Course", "url": "https://www.youtube.com/watch?v=3qBXWUpoPHo", "type": "YouTube"},
        {"title": "Official Angular Docs", "url": "https://angular.dev/", "type": "Docs"},
    ],
    "vue": [
        {"title": "Vue.js Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=FXpIoQ_rT_c", "type": "YouTube"},
        {"title": "Official Vue Docs", "url": "https://vuejs.org/guide/introduction.html", "type": "Docs"},
    ],
    "node.js": [
        {"title": "Node.js Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=Oe421EPjeBE", "type": "YouTube"},
        {"title": "Official Node.js Docs", "url": "https://nodejs.org/en/learn", "type": "Docs"},
    ],
    "django": [
        {"title": "Django Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=F5mRW0jo-U4", "type": "YouTube"},
        {"title": "Official Django Docs", "url": "https://docs.djangoproject.com/en/stable/", "type": "Docs"},
    ],
    "flask": [
        {"title": "Flask Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=Z1RJmh_OqeA", "type": "YouTube"},
        {"title": "Official Flask Docs", "url": "https://flask.palletsprojects.com/", "type": "Docs"},
    ],
    "fastapi": [
        {"title": "FastAPI Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=0sOvCWFmrtA", "type": "YouTube"},
        {"title": "Official FastAPI Docs", "url": "https://fastapi.tiangolo.com/tutorial/", "type": "Docs"},
    ],
    "machine learning": [
        {"title": "Machine Learning Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=NWONeJKn6kc", "type": "YouTube"},
        {"title": "Google's Machine Learning Crash Course", "url": "https://developers.google.com/machine-learning/crash-course", "type": "Free site"},
    ],
    "deep learning": [
        {"title": "Deep Learning Specialization Intro (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=VyWAvY2CF9c", "type": "YouTube"},
        {"title": "fast.ai Free Course", "url": "https://course.fast.ai/", "type": "Free site"},
    ],
    "nlp": [
        {"title": "NLP Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=fM4qTMfCoak", "type": "YouTube"},
        {"title": "Hugging Face NLP Course", "url": "https://huggingface.co/learn/nlp-course", "type": "Free site"},
    ],
    "computer vision": [
        {"title": "OpenCV Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=oXlwWbU8l2o", "type": "YouTube"},
        {"title": "OpenCV Docs & Tutorials", "url": "https://docs.opencv.org/4.x/d9/df8/tutorial_root.html", "type": "Docs"},
    ],
    "tensorflow": [
        {"title": "TensorFlow Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=tPYj3fFJGjk", "type": "YouTube"},
        {"title": "Official TensorFlow Tutorials", "url": "https://www.tensorflow.org/tutorials", "type": "Docs"},
    ],
    "pytorch": [
        {"title": "PyTorch Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=V_xro1bcAuA", "type": "YouTube"},
        {"title": "Official PyTorch Tutorials", "url": "https://pytorch.org/tutorials/", "type": "Docs"},
    ],
    "scikit-learn": [
        {"title": "scikit-learn Crash Course", "url": "https://www.youtube.com/watch?v=0Lt9w-BxKFQ", "type": "YouTube"},
        {"title": "Official scikit-learn Docs", "url": "https://scikit-learn.org/stable/tutorial/index.html", "type": "Docs"},
    ],
    "pandas": [
        {"title": "Pandas Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=vmEHCJofslg", "type": "YouTube"},
        {"title": "Official Pandas Docs", "url": "https://pandas.pydata.org/docs/getting_started/index.html", "type": "Docs"},
    ],
    "numpy": [
        {"title": "NumPy Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=QUT1VHiLmmI", "type": "YouTube"},
        {"title": "Official NumPy Docs", "url": "https://numpy.org/doc/stable/user/absolute_beginners.html", "type": "Docs"},
    ],
    "aws": [
        {"title": "AWS Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=SOTamWNgDKc", "type": "YouTube"},
        {"title": "AWS Free Tier & Training", "url": "https://aws.amazon.com/training/digital/", "type": "Free site"},
    ],
    "azure": [
        {"title": "Azure Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=NKEFWyqJ5XA", "type": "YouTube"},
        {"title": "Microsoft Learn: Azure", "url": "https://learn.microsoft.com/en-us/training/azure/", "type": "Free site"},
    ],
    "gcp": [
        {"title": "Google Cloud Full Course", "url": "https://www.youtube.com/watch?v=fZOz13joN0k", "type": "YouTube"},
        {"title": "Google Cloud Skills Boost (free tier)", "url": "https://www.cloudskillsboost.google/", "type": "Free site"},
    ],
    "docker": [
        {"title": "Docker Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=fqMOX6JJhGo", "type": "YouTube"},
        {"title": "Official Docker Docs", "url": "https://docs.docker.com/get-started/", "type": "Docs"},
    ],
    "kubernetes": [
        {"title": "Kubernetes Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=X48VuDVv0do", "type": "YouTube"},
        {"title": "Official Kubernetes Docs", "url": "https://kubernetes.io/docs/tutorials/", "type": "Docs"},
    ],
    "git": [
        {"title": "Git & GitHub Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "type": "YouTube"},
        {"title": "Official Git Docs", "url": "https://git-scm.com/doc", "type": "Docs"},
    ],
    "linux": [
        {"title": "Linux Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=sWbUDq4S6Y8", "type": "YouTube"},
        {"title": "Linux Journey (free site)", "url": "https://linuxjourney.com/", "type": "Free site"},
    ],
    "html": [
        {"title": "HTML Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=pQN-pnXPaVg", "type": "YouTube"},
        {"title": "MDN HTML Docs", "url": "https://developer.mozilla.org/en-US/docs/Web/HTML", "type": "Docs"},
    ],
    "css": [
        {"title": "CSS Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=1Rs2ND1ryYc", "type": "YouTube"},
        {"title": "MDN CSS Docs", "url": "https://developer.mozilla.org/en-US/docs/Web/CSS", "type": "Docs"},
    ],
    "rest api": [
        {"title": "REST API Concepts (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=lsMQRaeKNDk", "type": "YouTube"},
        {"title": "REST API Tutorial", "url": "https://restfulapi.net/", "type": "Free site"},
    ],
    "graphql": [
        {"title": "GraphQL Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=ed8SzALpx1Q", "type": "YouTube"},
        {"title": "Official GraphQL Docs", "url": "https://graphql.org/learn/", "type": "Docs"},
    ],
    "mongodb": [
        {"title": "MongoDB Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=c2M-rlkkT5o", "type": "YouTube"},
        {"title": "MongoDB University (free)", "url": "https://university.mongodb.com/", "type": "Free site"},
    ],
    "postgresql": [
        {"title": "PostgreSQL Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=qw--VYLpxG4", "type": "YouTube"},
        {"title": "Official PostgreSQL Tutorial", "url": "https://www.postgresql.org/docs/current/tutorial.html", "type": "Docs"},
    ],
    "mysql": [
        {"title": "MySQL Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=9ylj9NR0Lcg", "type": "YouTube"},
        {"title": "MySQL Tutorial (W3Schools)", "url": "https://www.w3schools.com/mysql/", "type": "Free site"},
    ],
    "data analysis": [
        {"title": "Data Analysis Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=r-uOLxNrNk8", "type": "YouTube"},
        {"title": "Kaggle Free Courses", "url": "https://www.kaggle.com/learn", "type": "Free site"},
    ],
    "data visualization": [
        {"title": "Data Visualization Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=a9UrKTVEeZA", "type": "YouTube"},
        {"title": "Kaggle: Data Visualization", "url": "https://www.kaggle.com/learn/data-visualization", "type": "Free site"},
    ],
    "excel": [
        {"title": "Excel Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=Vl0H-qTclOg", "type": "YouTube"},
        {"title": "Microsoft Excel Help & Training", "url": "https://support.microsoft.com/en-us/excel", "type": "Docs"},
    ],
    "power bi": [
        {"title": "Power BI Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=AGrl-H87pRU", "type": "YouTube"},
        {"title": "Microsoft Learn: Power BI", "url": "https://learn.microsoft.com/en-us/power-bi/", "type": "Free site"},
    ],
    "tableau": [
        {"title": "Tableau Full Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=TPMlZxRRaBQ", "type": "YouTube"},
        {"title": "Tableau Free Training Videos", "url": "https://www.tableau.com/learn/training", "type": "Free site"},
    ],
    "communication": [
        {"title": "Communication Skills (freeCodeCamp-style talks)", "url": "https://www.youtube.com/results?search_query=professional+communication+skills+course", "type": "YouTube"},
        {"title": "HBR: Better Business Writing", "url": "https://hbr.org/topic/subject/business-communication", "type": "Free site"},
    ],
    "leadership": [
        {"title": "Leadership Skills Course", "url": "https://www.youtube.com/results?search_query=leadership+skills+free+course", "type": "YouTube"},
        {"title": "MindTools: Leadership", "url": "https://www.mindtools.com/leadership-skills", "type": "Free site"},
    ],
    "project management": [
        {"title": "Project Management Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=Cmy2FR3vYNo", "type": "YouTube"},
        {"title": "Google Project Management (free audit)", "url": "https://www.coursera.org/professional-certificates/google-project-management", "type": "Free site"},
    ],
    "agile": [
        {"title": "Agile & Scrum Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=502ILHjX9EE", "type": "YouTube"},
        {"title": "Atlassian: Agile Coach", "url": "https://www.atlassian.com/agile", "type": "Free site"},
    ],
    "scrum": [
        {"title": "Scrum Master Course (freeCodeCamp)", "url": "https://www.youtube.com/watch?v=9TycLR0TqFA", "type": "YouTube"},
        {"title": "Scrum.org Free Resources", "url": "https://www.scrum.org/resources", "type": "Free site"},
    ],
}


def get_resources_for_skill(skill: str) -> list:
    """Returns curated resources for a skill, or an empty list if none exist."""
    return SKILL_RESOURCES.get(skill.lower(), [])
