from fastapi import Depends,FastAPI,HTTPException,status
from sqlalchemy import func, select,text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import Base,engine,get_db
from models import VisitModel
from schemas import VisitResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini-VPC Lab API", version="1.0.0")

def build_stats(db: Session) -> VisitResponse:
    total = db.scalar(select(func.count(VisitModel.id)))
    last_visit = db.scalar(select(func.max(VisitModel.created_at)))
    return VisitResponse(total=total, last_visit=last_visit)


@app.get("/healthz", status_code=status.HTTP_200_OK)
def healthz():
    return  {"status": "healthy"}

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not reachable",
        )
    return {"database": "reachable"}


@app.get("/visits", response_model=VisitResponse)
def get_visits(db: Session = Depends(get_db)):
    return build_stats(db)

@app.post(
    "/visits",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
)

def create_visit(db: Session = Depends(get_db)):
    db.add(VisitModel())
    db.commit()
    return build_stats(db)