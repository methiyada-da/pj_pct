from django import template


register = template.Library()


COURSE_COVER_BY_GROUP = {
    "การศึกษาและการสอน": "education.png",
    "คณิตศาสตร์และสถิติ": "mathematics.png",
    "ภาษาและการสื่อสาร": "language.png",
    "ระบบคอมพิวเตอร์และเครือข่าย": "networks.png",
    "ระบบสารสนเทศและข้อมูล": "data.png",
    "วิทยาศาสตร์": "science.png",
    "วิศวกรรม": "engineering.png",
    "สังคมและการพัฒนาตนเอง": "society.png",
    "สื่อดิจิทัล": "digital-media.png",
    "โครงงานและวิชาชีพ": "career-project.png",
    "โปรแกรมและซอฟต์แวร์": "programming.png",
}


@register.filter
def course_cover_path(tutor_course):
    """คืนพาธรูปปกสำรองตามกลุ่มวิชา เมื่อคอร์สยังไม่มีรูปที่อัปโหลด"""
    try:
        group_name = tutor_course.crs_id.cg_id.cg_name
    except (AttributeError, TypeError):
        group_name = ""

    filename = COURSE_COVER_BY_GROUP.get(group_name, "education.png")
    return f"images/course_covers/{filename}"
